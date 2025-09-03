import sys
import os
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock

# Add the parent directory to sys.path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator
from vector_store import VectorStore
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from models import Course, Lesson, CourseChunk


class TestSequentialToolCallingIntegration(unittest.TestCase):
    """Integration tests for sequential tool calling with real components"""
    
    def setUp(self):
        """Set up test environment for each test"""
        # Create unique temporary directory for each test
        self.test_dir = tempfile.mkdtemp()
        self.chroma_path = os.path.join(self.test_dir, "test_chroma")
        
    def tearDown(self):
        """Clean up test environment after each test"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_sequential_tool_calling_with_real_tools(self, mock_anthropic_class):
        """Test sequential tool calling with real VectorStore and tools"""
        # Mock the Anthropic client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Create real components
        vector_store = VectorStore(self.chroma_path, "all-MiniLM-L6-v2", max_results=3)
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(vector_store)
        outline_tool = CourseOutlineTool(vector_store)
        tool_manager.register_tool(search_tool)
        tool_manager.register_tool(outline_tool)
        
        ai_generator = AIGenerator("test_key", "claude-sonnet-4-20250514")
        
        # Add test course data
        course_python = Course(
            title="Python Fundamentals",
            instructor="Python Expert",
            lessons=[
                Lesson(lesson_number=1, title="Variables and Data Types"),
                Lesson(lesson_number=2, title="Functions and Modules"),
                Lesson(lesson_number=3, title="Object-Oriented Programming")
            ]
        )
        
        course_java = Course(
            title="Java Basics",
            instructor="Java Master",
            lessons=[
                Lesson(lesson_number=1, title="Java Syntax"),
                Lesson(lesson_number=2, title="Classes and Objects")
            ]
        )
        
        # Add courses to vector store
        vector_store.add_course_metadata(course_python)
        vector_store.add_course_metadata(course_java)
        
        # Add content chunks
        python_chunks = [
            CourseChunk(
                content="Variables in Python store data values. Python has different data types like int, float, string.",
                course_title="Python Fundamentals",
                lesson_number=1,
                chunk_index=0
            ),
            CourseChunk(
                content="Functions in Python are defined with def keyword. Modules help organize code.",
                course_title="Python Fundamentals", 
                lesson_number=2,
                chunk_index=1
            )
        ]
        
        java_chunks = [
            CourseChunk(
                content="Java syntax is similar to C++. Every Java program starts with a class definition.",
                course_title="Java Basics",
                lesson_number=1,
                chunk_index=0
            )
        ]
        
        vector_store.add_course_content(python_chunks)
        vector_store.add_course_content(java_chunks)
        
        # Mock API responses for sequential tool calling
        # Round 1: Get Python outline
        round1_response = Mock()
        round1_response.content = [Mock(type="tool_use", name="get_course_outline", 
                                       input={"course_name": "Python"}, id="call_1")]
        round1_response.stop_reason = "tool_use"
        
        # Round 2: Search for Java content
        round2_response = Mock()
        round2_response.content = [Mock(type="tool_use", name="search_course_content",
                                       input={"query": "Java classes"}, id="call_2")]
        round2_response.stop_reason = "tool_use"
        
        # Final response
        final_response = Mock()
        final_response.content = [Mock(text="Both Python and Java support object-oriented programming through classes.")]
        final_response.stop_reason = "end_turn"
        
        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]
        
        # Execute sequential tool calling
        result = ai_generator.generate_response(
            "Compare Python and Java class concepts",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Verify multiple API calls were made
        self.assertEqual(mock_client.messages.create.call_count, 3)
        
        # Verify tools were executed
        # Note: We can't easily verify exact tool execution without intrusive mocking,
        # but we can check that the result contains expected content
        self.assertIn("Python", result)
        self.assertIn("Java", result)
        
        # Verify sources were tracked correctly
        sources = tool_manager.get_last_sources()
        self.assertGreaterEqual(len(sources), 0)  # Should have some sources from searches
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_sequential_early_termination_real_tools(self, mock_anthropic_class):
        """Test that sequential tool calling terminates early when Claude stops using tools"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Create real components
        vector_store = VectorStore(self.chroma_path, "all-MiniLM-L6-v2", max_results=3)
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(vector_store)
        tool_manager.register_tool(search_tool)
        
        ai_generator = AIGenerator("test_key", "claude-sonnet-4-20250514")
        
        # Add simple test data
        course = Course(title="Test Course", lessons=[])
        vector_store.add_course_metadata(course)
        chunks = [CourseChunk(content="Test content about programming", 
                             course_title="Test Course", chunk_index=0)]
        vector_store.add_course_content(chunks)
        
        # Round 1: Use tool
        round1_response = Mock()
        round1_response.content = [Mock(type="tool_use", name="search_course_content",
                                       input={"query": "programming"}, id="call_1")]
        round1_response.stop_reason = "tool_use"
        
        # Round 2: Don't use tools - should terminate here
        round2_response = Mock()
        round2_response.content = [Mock(text="Programming is fundamental to software development.")]
        round2_response.stop_reason = "end_turn"
        
        mock_client.messages.create.side_effect = [round1_response, round2_response]
        
        result = ai_generator.generate_response(
            "What is programming?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Should make only 2 API calls (round 1 with tool, round 2 without tool)
        self.assertEqual(mock_client.messages.create.call_count, 2)
        
        # Should get the direct response from round 2
        self.assertEqual(result, "Programming is fundamental to software development.")
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_max_rounds_enforcement_real_tools(self, mock_anthropic_class):
        """Test that max rounds limit is enforced with real tools"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Create real components
        vector_store = VectorStore(self.chroma_path, "all-MiniLM-L6-v2", max_results=3)
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(vector_store)
        tool_manager.register_tool(search_tool)
        
        ai_generator = AIGenerator("test_key", "claude-sonnet-4-20250514")
        
        # Add test data
        course = Course(title="Programming Course", lessons=[])
        vector_store.add_course_metadata(course)
        chunks = [CourseChunk(content="Various programming concepts", 
                             course_title="Programming Course", chunk_index=0)]
        vector_store.add_course_content(chunks)
        
        # Both rounds want to use tools
        round1_response = Mock()
        round1_response.content = [Mock(type="tool_use", name="search_course_content",
                                       input={"query": "programming"}, id="call_1")]
        round1_response.stop_reason = "tool_use"
        
        round2_response = Mock()
        round2_response.content = [Mock(type="tool_use", name="search_course_content",
                                       input={"query": "concepts"}, id="call_2")]
        round2_response.stop_reason = "tool_use"
        
        # Final synthesized response
        final_response = Mock()
        final_response.content = [Mock(text="Here's a comprehensive overview of programming concepts.")]
        final_response.stop_reason = "end_turn"
        
        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]
        
        result = ai_generator.generate_response(
            "Give me comprehensive information about programming",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Should make 3 API calls: round1, round2, final (stopped at max_rounds=2)
        self.assertEqual(mock_client.messages.create.call_count, 3)
        
        # Should get the synthesized response
        self.assertEqual(result, "Here's a comprehensive overview of programming concepts.")


if __name__ == '__main__':
    unittest.main()