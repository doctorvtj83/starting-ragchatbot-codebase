import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Available Tools:
- **Content Search Tool**: For searching specific course content and detailed educational materials
- **Course Outline Tool**: For getting course outlines with title, course link, instructor, and complete lesson lists (numbers and titles)

Tool Usage Guidelines:
- **Sequential Tool Calls**: You can make up to 2 rounds of tool calls to gather comprehensive information
- **Multi-step Queries**: For complex questions, use the first tool call to gather initial information, then use a second call if needed based on those results
- **Content questions**: Use the content search tool for specific course material questions
- **Outline questions**: Use the outline tool for course structure, lesson lists, or course overview requests
- **Comparative queries**: First gather information about each subject, then compare
- **Follow-up searches**: If initial results suggest related topics or courses, make additional targeted searches
- Synthesize results from all tool calls into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Sequential Tool Call Examples:
- "Compare topic X in course A with course B" → Search course A for topic X, then search course B for topic X
- "Find courses similar to lesson 5 of course Y" → Get outline of course Y to understand lesson 5, then search for similar content
- "What topics are covered after lesson 3 in course Z" → Get course Z outline, then search for content in later lessons

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use appropriate tool(s) first, then answer
- **Course outline requests**: Always use the outline tool to provide course title, course link, and complete lesson information
- **Complex queries**: Use sequential tool calls to gather comprehensive information before responding
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the outline tool"
 - Do not explain your tool usage strategy

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
5. **Comprehensive** - Use multiple tool calls when needed for complete answers
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            # Use default max_rounds of 2, but could be made configurable
            return self._handle_tool_execution(response, api_params, tool_manager, max_rounds=2)
        
        # Return direct response
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager, max_rounds: int = 2):
        """
        Handle execution of tool calls with support for sequential rounds.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool calling rounds (default: 2)
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        current_response = initial_response
        round_count = 0
        
        # Sequential tool execution loop
        while (round_count < max_rounds and 
               current_response.stop_reason == "tool_use" and 
               tool_manager):
            
            round_count += 1
            
            # Add AI's tool use response to message history
            messages.append({"role": "assistant", "content": current_response.content})
            
            # Execute all tool calls in current round and collect results
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    tool_result = tool_manager.execute_tool(
                        content_block.name, 
                        **content_block.input
                    )
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })
            
            # Add tool results as user message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            
            # Check if we've reached max rounds - if so, make final call without tools
            if round_count >= max_rounds:
                break
            
            # Prepare next API call with tools still available for potential next round
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                "tools": base_params.get("tools", []),
                "tool_choice": {"type": "auto"}
            }
            
            # Make next API call to see if Claude wants to use more tools
            try:
                current_response = self.client.messages.create(**next_params)
            except Exception as e:
                # If API call fails, break the loop and generate final response
                print(f"Error in tool execution round {round_count}: {e}")
                break
        
        # Generate final response without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # If we exited the loop due to no tool use, use the current response
        if current_response.stop_reason != "tool_use":
            return current_response.content[0].text
        
        # Otherwise, make a final call without tools to get the synthesized response
        try:
            final_response = self.client.messages.create(**final_params)
            return final_response.content[0].text
        except Exception as e:
            print(f"Error in final response generation: {e}")
            return "I apologize, but I encountered an error while generating the final response."