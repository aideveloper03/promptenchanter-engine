"""
AI Deep Research Service for PromptEnchanter
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
import re
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from app.models.schemas import (
    ResearchRequest, ResearchResponse, ResearchResult, ResearchTopic, 
    WAPIRequest, WAPIMessage, ResearchDepth
)
from app.services.wapi_client import wapi_client
from app.utils.logger import get_logger, RequestLogger
from app.utils.cache import ResearchCache
from app.utils.security import hash_content, sanitize_input
from app.config.settings import get_settings

settings = get_settings()
logger = get_logger(__name__)


class ResearchService:
    """AI-powered research service with internet access"""
    
    def __init__(self):
        self.max_search_results = 10
        self.max_content_length = 5000
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self._semaphore = asyncio.Semaphore(5)  # Limit concurrent web requests
    
    async def conduct_research(
        self, 
        query: str, 
        depth: ResearchDepth = ResearchDepth.BASIC,
        request_logger: Optional[RequestLogger] = None
    ) -> ResearchResponse:
        """Conduct comprehensive research on a query"""
        
        if not request_logger:
            request_logger = RequestLogger("research", "research_service")
        
        start_time = time.time()
        query = sanitize_input(query, 1000)
        
        request_logger.info("Starting research", query=query, depth=depth)
        
        # Check cache first
        query_hash = hash_content(f"{query}:{depth}")
        cached_research = await ResearchCache.get_research(query_hash)
        if cached_research:
            request_logger.info("Research served from cache")
            return ResearchResponse(**cached_research)
        
        try:
            # Step 1: Analyze query and identify research topics
            research_topics = await self._identify_research_topics(query, depth, request_logger)
            
            # Step 2: Research each topic
            research_results = []
            for topic in research_topics:
                result = await self._research_topic(topic, request_logger)
                if result:
                    research_results.append(result)
            
            # Step 3: Synthesize final research
            if research_results:
                final_research = await self._synthesize_research(query, research_results, request_logger)
                if final_research:
                    research_results = [final_research]
            
            # Calculate total sources
            total_sources = sum(len(result.sources) for result in research_results)
            
            processing_time = (time.time() - start_time) * 1000
            
            response = ResearchResponse(
                query=query,
                results=research_results,
                total_sources=total_sources,
                processing_time_ms=int(processing_time)
            )
            
            # Cache the response
            await ResearchCache.set_research(query_hash, response.dict())
            
            request_logger.info(
                "Research completed",
                topics_researched=len(research_topics),
                total_sources=total_sources,
                processing_time_ms=int(processing_time)
            )
            
            return response
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            request_logger.error(
                "Research failed",
                error=str(e),
                processing_time_ms=int(processing_time)
            )
            # Return empty research result instead of failing
            return ResearchResponse(
                query=query,
                results=[],
                total_sources=0,
                processing_time_ms=int(processing_time)
            )
    
    async def _identify_research_topics(
        self, 
        query: str, 
        depth: ResearchDepth,
        request_logger: RequestLogger
    ) -> List[ResearchTopic]:
        """Use AI to identify what topics need research"""
        
        depth_instructions = {
            ResearchDepth.BASIC: "Identify 1-2 key topics that need research.",
            ResearchDepth.MEDIUM: "Identify 3-4 important topics that need research.",
            ResearchDepth.HIGH: "Identify 5-6 comprehensive topics that need research."
        }
        
        system_prompt = f"""You are a research analyst. Analyze the user's query and determine if it needs research and what specific topics should be researched.

{depth_instructions[depth]}

Respond with a JSON object in this format:
{{
    "needs_research": true/false,
    "topics": [
        {{
            "topic": "specific topic to research",
            "importance": 0.0-1.0,
            "subtopics": ["subtopic1", "subtopic2"]
        }}
    ]
}}

If the query is simple and doesn't need research (like basic math, simple definitions, or personal opinions), set needs_research to false."""
        
        try:
            request = WAPIRequest(
                model="gpt-4o-mini",
                messages=[
                    WAPIMessage(role="system", content=system_prompt),
                    WAPIMessage(role="user", content=f"Query: {query}")
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            response = await wapi_client.chat_completion(request, request_logger, use_cache=True)
            
            if response.choices and response.choices[0].message.content:
                import json
                result = json.loads(response.choices[0].message.content)
                
                if not result.get("needs_research", False):
                    return []
                
                topics = []
                for topic_data in result.get("topics", []):
                    topics.append(ResearchTopic(
                        topic=topic_data["topic"],
                        importance=topic_data.get("importance", 0.5),
                        subtopics=topic_data.get("subtopics", [])
                    ))
                
                return topics
                
        except Exception as e:
            request_logger.error(f"Failed to identify research topics: {e}")
        
        return []
    
    async def _research_topic(
        self, 
        topic: ResearchTopic, 
        request_logger: RequestLogger
    ) -> Optional[ResearchResult]:
        """Research a specific topic"""
        
        request_logger.debug("Researching topic", topic=topic.topic)
        
        # Step 1: Search for information
        search_results = await self._search_web(topic.topic, request_logger)
        
        if not search_results:
            return None
        
        # Step 2: Extract and parse content from top results
        content_data = await self._extract_content(search_results[:5], request_logger)
        
        if not content_data:
            return None
        
        # Step 3: Use AI to synthesize the research
        research_content = await self._synthesize_content(topic, content_data, request_logger)
        
        if research_content:
            sources = [item["url"] for item in content_data]
            return ResearchResult(
                topic=topic.topic,
                content=research_content,
                sources=sources,
                confidence=min(0.9, topic.importance + 0.1)
            )
        
        return None
    
    async def _search_web(self, query: str, request_logger: RequestLogger) -> List[Dict[str, Any]]:
        """Search the web using DuckDuckGo"""
        
        # Check cache first
        query_hash = hash_content(query)
        cached_results = await ResearchCache.get_search_results(query_hash)
        if cached_results:
            return cached_results
        
        try:
            async with self._semaphore:
                # Use DuckDuckGo search
                with DDGS() as ddgs:
                    results = list(ddgs.text(
                        keywords=query,
                        max_results=self.max_search_results,
                        safesearch='moderate'
                    ))
                
                # Format results
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", "")
                    })
                
                # Cache results
                await ResearchCache.set_search_results(query_hash, formatted_results)
                
                request_logger.debug(f"Found {len(formatted_results)} search results for: {query}")
                return formatted_results
                
        except Exception as e:
            request_logger.error(f"Web search failed for '{query}': {e}")
            return []
    
    async def _extract_content(
        self, 
        search_results: List[Dict[str, Any]], 
        request_logger: RequestLogger
    ) -> List[Dict[str, Any]]:
        """Extract content from web pages"""
        
        content_data = []
        
        async def extract_single(result):
            try:
                async with self._semaphore:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(
                            result["url"],
                            headers={"User-Agent": "Mozilla/5.0 (PromptEnchanter Research Bot)"},
                            follow_redirects=True
                        )
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # Remove script and style elements
                            for script in soup(["script", "style"]):
                                script.extract()
                            
                            # Get text content
                            text = soup.get_text()
                            
                            # Clean up text
                            lines = (line.strip() for line in text.splitlines())
                            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                            text = ' '.join(chunk for chunk in chunks if chunk)
                            
                            # Truncate if too long
                            if len(text) > self.max_content_length:
                                text = text[:self.max_content_length] + "..."
                            
                            return {
                                "url": result["url"],
                                "title": result["title"],
                                "content": text,
                                "snippet": result["snippet"]
                            }
            except Exception as e:
                request_logger.debug(f"Failed to extract content from {result['url']}: {e}")
                return None
        
        # Extract content from multiple URLs concurrently
        tasks = [extract_single(result) for result in search_results]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if result and not isinstance(result, Exception):
                content_data.append(result)
        
        request_logger.debug(f"Extracted content from {len(content_data)} pages")
        return content_data
    
    async def _synthesize_content(
        self, 
        topic: ResearchTopic, 
        content_data: List[Dict[str, Any]], 
        request_logger: RequestLogger
    ) -> Optional[str]:
        """Use AI to synthesize research content"""
        
        # Prepare content for AI
        content_summary = "\n\n".join([
            f"Source: {item['title']}\nURL: {item['url']}\nContent: {item['content'][:1000]}..."
            for item in content_data[:3]  # Limit to top 3 sources to avoid token limits
        ])
        
        system_prompt = f"""You are a research synthesizer. Create a comprehensive, well-structured research summary on the topic: "{topic.topic}"

Guidelines:
1. Synthesize information from multiple sources
2. Focus on accuracy and relevance
3. Include key facts, statistics, and insights
4. Structure the content logically
5. Keep it concise but comprehensive
6. Don't mention the sources in the content (they're tracked separately)

Topic subtopics to cover if relevant: {', '.join(topic.subtopics)}"""
        
        try:
            request = WAPIRequest(
                model="gpt-4o",
                messages=[
                    WAPIMessage(role="system", content=system_prompt),
                    WAPIMessage(role="user", content=f"Research sources:\n\n{content_summary}")
                ],
                temperature=0.4,
                max_tokens=2000
            )
            
            response = await wapi_client.chat_completion(request, request_logger, use_cache=True)
            
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
                
        except Exception as e:
            request_logger.error(f"Failed to synthesize content for topic '{topic.topic}': {e}")
        
        return None
    
    async def _synthesize_research(
        self, 
        original_query: str, 
        research_results: List[ResearchResult], 
        request_logger: RequestLogger
    ) -> Optional[ResearchResult]:
        """Synthesize all research results into final comprehensive research"""
        
        if len(research_results) <= 1:
            return research_results[0] if research_results else None
        
        # Combine all research content
        combined_content = "\n\n".join([
            f"## {result.topic}\n{result.content}"
            for result in research_results
        ])
        
        system_prompt = f"""You are a master research synthesizer. Create a comprehensive, final research document that combines all the research topics into a cohesive response to the original query.

Original Query: "{original_query}"

Guidelines:
1. Create a unified, well-structured response
2. Integrate insights from all research topics
3. Remove redundancy while preserving key information
4. Ensure logical flow and coherence
5. Focus on answering the original query
6. Make it comprehensive yet readable"""
        
        try:
            request = WAPIRequest(
                model="gpt-4o",
                messages=[
                    WAPIMessage(role="system", content=system_prompt),
                    WAPIMessage(role="user", content=f"Research content to synthesize:\n\n{combined_content}")
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            response = await wapi_client.chat_completion(request, request_logger, use_cache=True)
            
            if response.choices and response.choices[0].message.content:
                # Combine all sources
                all_sources = []
                for result in research_results:
                    all_sources.extend(result.sources)
                
                return ResearchResult(
                    topic=f"Comprehensive Research: {original_query}",
                    content=response.choices[0].message.content.strip(),
                    sources=list(set(all_sources)),  # Remove duplicates
                    confidence=sum(r.confidence for r in research_results) / len(research_results)
                )
                
        except Exception as e:
            request_logger.error(f"Failed to synthesize final research: {e}")
        
        return research_results[0] if research_results else None


# Global research service instance
research_service = ResearchService()