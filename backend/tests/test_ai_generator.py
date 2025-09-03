import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch, call
import json

# Add the parent directory to sys.path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator


class MockAnthropicResponse:
    """Mock response from Anthropic API"""
    def __init__(self, content, stop_reason="end_turn", tool_calls=None):
        self.content = content if isinstance(content, list) else [Mock(text=content, type="text")]
        self.stop_reason = stop_reason
        
        if tool_calls:
            # Add tool use blocks to content
            for tool_call in tool_calls:
                tool_block = Mock()
                tool_block.type = "tool_use"
                tool_block.name = tool_call["name"]
                tool_block.input = tool_call["input"]
                tool_block.id = tool_call.get("id", "tool_call_1")
                self.content.append(tool_block)


class TestAIGenerator(unittest.TestCase):
    """Test suite for AIGenerator CourseSearchTool integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "test_api_key"
        self.model = "claude-sonnet-4-20250514"
        
        # Mock the Anthropic client
        self.mock_anthropic_client = Mock()
        
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = self.mock_anthropic_client
            self.ai_generator = AIGenerator(self.api_key, self.model)
    
    def test_generate_response_without_tools(self):
        """Test response generation without tools"""
        # Mock API response
        mock_response = MockAnthropicResponse("This is a direct response without tools")
        self.mock_anthropic_client.messages.create.return_value = mock_response
        
        result = self.ai_generator.generate_response("What is Python?")
        
        # Verify API was called correctly
        self.mock_anthropic_client.messages.create.assert_called_once()
        call_args = self.mock_anthropic_client.messages.create.call_args
        
        # Check basic parameters
        self.assertEqual(call_args.kwargs["model"], self.model)
        self.assertEqual(call_args.kwargs["temperature"], 0)
        self.assertEqual(call_args.kwargs["max_tokens"], 800)
        
        # Check message content
        messages = call_args.kwargs["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "What is Python?")
        
        # Check system prompt
        self.assertIn("course materials", call_args.kwargs["system"])
        
        self.assertEqual(result, "This is a direct response without tools")
    
    def test_generate_response_with_tools_no_tool_use(self):
        """Test response with tools available but not used"""
        mock_tools = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        ]
        
        mock_response = MockAnthropicResponse("Direct answer without using tools")
        self.mock_anthropic_client.messages.create.return_value = mock_response
        
        result = self.ai_generator.generate_response(
            "What is 2+2?", 
            tools=mock_tools
        )
        
        # Verify tools were provided in API call
        call_args = self.mock_anthropic_client.messages.create.call_args
        self.assertEqual(call_args.kwargs["tools"], mock_tools)
        self.assertEqual(call_args.kwargs["tool_choice"], {"type": "auto"})
        
        self.assertEqual(result, "Direct answer without using tools")
    
    def test_generate_response_with_tool_execution(self):
        """Test response generation with tool execution"""
        # Setup mock tools and tool manager
        mock_tools = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        ]
        
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "[Python Basics - Lesson 1]\nPython is a programming language"
        
        # Mock initial response with tool use
        initial_response = MockAnthropicResponse(
            content=[],
            stop_reason="tool_use",
            tool_calls=[{
                "name": "search_course_content",
                "input": {"query": "What is Python"},
                "id": "tool_call_123"
            }]
        )
        
        # Mock final response after tool execution
        final_response = MockAnthropicResponse("Based on the search results, Python is a programming language used for various applications.")
        
        self.mock_anthropic_client.messages.create.side_effect = [initial_response, final_response]
        
        result = self.ai_generator.generate_response(
            "What is Python?",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="What is Python"
        )
        
        # Verify two API calls were made
        self.assertEqual(self.mock_anthropic_client.messages.create.call_count, 2)
        
        # Check final result
        self.assertEqual(result, "Based on the search results, Python is a programming language used for various applications.")
    
    def test_conversation_history_included(self):
        """Test that conversation history is included in system prompt"""
        mock_response = MockAnthropicResponse("Response with history context")
        self.mock_anthropic_client.messages.create.return_value = mock_response
        
        history = "User: Previous question\nAssistant: Previous answer"
        
        self.ai_generator.generate_response("New question", conversation_history=history)
        
        # Check that history was included in system prompt
        call_args = self.mock_anthropic_client.messages.create.call_args
        system_content = call_args.kwargs["system"]
        self.assertIn("Previous conversation:", system_content)
        self.assertIn("Previous question", system_content)
        self.assertIn("Previous answer", system_content)
    
    def test_multiple_tool_calls(self):
        """Test handling of multiple tool calls in single response"""
        mock_tools = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        ]
        
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Search result 1",
            "Search result 2"
        ]
        
        # Mock response with multiple tool calls
        initial_response = MockAnthropicResponse(
            content=[],
            stop_reason="tool_use",
            tool_calls=[
                {"name": "search_course_content", "input": {"query": "topic 1"}, "id": "call_1"},
                {"name": "search_course_content", "input": {"query": "topic 2"}, "id": "call_2"}
            ]
        )
        
        final_response = MockAnthropicResponse("Combined response from multiple searches")
        
        self.mock_anthropic_client.messages.create.side_effect = [initial_response, final_response]
        
        result = self.ai_generator.generate_response(
            "Compare topics",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify both tools were executed
        self.assertEqual(mock_tool_manager.execute_tool.call_count, 2)
        expected_calls = [
            call("search_course_content", query="topic 1"),
            call("search_course_content", query="topic 2")
        ]
        mock_tool_manager.execute_tool.assert_has_calls(expected_calls)
    
    def test_tool_execution_error_handling(self):
        """Test handling of tool execution errors"""
        mock_tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]
        
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool execution failed: Database error"
        
        initial_response = MockAnthropicResponse(
            content=[],
            stop_reason="tool_use", 
            tool_calls=[{"name": "search_course_content", "input": {"query": "test"}, "id": "call_1"}]
        )
        
        final_response = MockAnthropicResponse("I apologize, there was an error searching the content.")
        
        self.mock_anthropic_client.messages.create.side_effect = [initial_response, final_response]
        
        result = self.ai_generator.generate_response(
            "Search question",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Should handle error gracefully and return final response
        self.assertEqual(result, "I apologize, there was an error searching the content.")
    
    def test_system_prompt_structure(self):
        """Test that system prompt contains expected instructions"""
        mock_response = MockAnthropicResponse("Test response")
        self.mock_anthropic_client.messages.create.return_value = mock_response
        
        self.ai_generator.generate_response("Test query")
        
        call_args = self.mock_anthropic_client.messages.create.call_args
        system_prompt = call_args.kwargs["system"]
        
        # Check key elements of system prompt
        self.assertIn("course materials", system_prompt)
        self.assertIn("Content Search Tool", system_prompt)
        self.assertIn("Course Outline Tool", system_prompt)
        self.assertIn("Brief, Concise and focused", system_prompt)
        self.assertIn("Educational", system_prompt)
    
    def test_api_parameters(self):
        """Test that API parameters are set correctly"""
        mock_response = MockAnthropicResponse("Test response")
        self.mock_anthropic_client.messages.create.return_value = mock_response
        
        self.ai_generator.generate_response("Test query")
        
        call_args = self.mock_anthropic_client.messages.create.call_args
        
        # Check that base parameters are applied
        self.assertEqual(call_args.kwargs["model"], "claude-sonnet-4-20250514")
        self.assertEqual(call_args.kwargs["temperature"], 0)
        self.assertEqual(call_args.kwargs["max_tokens"], 800)
    
    def test_tool_call_message_flow(self):
        """Test the message flow during tool execution"""
        mock_tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search results"
        
        # Create mock tool content block
        tool_content = Mock()
        tool_content.type = "tool_use"
        tool_content.name = "search_course_content"
        tool_content.input = {"query": "test"}
        tool_content.id = "call_123"
        
        initial_response = Mock()
        initial_response.content = [tool_content]
        initial_response.stop_reason = "tool_use"
        
        final_response = MockAnthropicResponse("Final response")
        
        self.mock_anthropic_client.messages.create.side_effect = [initial_response, final_response]
        
        result = self.ai_generator.generate_response(
            "Test query",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Check that second API call has proper message structure
        second_call_args = self.mock_anthropic_client.messages.create.call_args_list[1]
        messages = second_call_args.kwargs["messages"]
        
        # Should have: user message, assistant message with tool use, user message with tool results
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["role"], "user")  # Original query
        self.assertEqual(messages[1]["role"], "assistant")  # Tool use response
        self.assertEqual(messages[2]["role"], "user")  # Tool results
        
        # Check tool results format
        tool_results = messages[2]["content"]
        self.assertEqual(len(tool_results), 1)
        self.assertEqual(tool_results[0]["type"], "tool_result")
        self.assertEqual(tool_results[0]["tool_use_id"], "call_123")
        self.assertEqual(tool_results[0]["content"], "Search results")


if __name__ == '__main__':
    unittest.main()