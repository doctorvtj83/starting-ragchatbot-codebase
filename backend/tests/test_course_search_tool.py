import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any

# Add the parent directory to sys.path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchTool(unittest.TestCase):
    """Test suite for CourseSearchTool.execute method"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock vector store
        self.mock_vector_store = Mock()
        self.search_tool = CourseSearchTool(self.mock_vector_store)
    
    def test_successful_search_with_results(self):
        """Test successful search returning results"""
        # Mock search results
        mock_results = SearchResults(
            documents=["This is course content about Python programming", "More Python content"],
            metadata=[
                {"course_title": "Python Basics", "lesson_number": 1},
                {"course_title": "Python Basics", "lesson_number": 2}
            ],
            distances=[0.1, 0.2],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"
        
        # Execute search
        result = self.search_tool.execute("Python programming")
        
        # Verify search was called correctly
        self.mock_vector_store.search.assert_called_once_with(
            query="Python programming",
            course_name=None,
            lesson_number=None
        )
        
        # Verify result formatting
        self.assertIn("[Python Basics - Lesson 1]", result)
        self.assertIn("[Python Basics - Lesson 2]", result)
        self.assertIn("This is course content about Python programming", result)
        self.assertIn("More Python content", result)
    
    def test_search_with_course_filter(self):
        """Test search with course name filter"""
        mock_results = SearchResults(
            documents=["Filtered content"],
            metadata=[{"course_title": "Advanced Python", "lesson_number": 3}],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.return_value = None
        
        result = self.search_tool.execute("functions", course_name="Advanced Python")
        
        self.mock_vector_store.search.assert_called_once_with(
            query="functions",
            course_name="Advanced Python",
            lesson_number=None
        )
        
        self.assertIn("[Advanced Python - Lesson 3]", result)
    
    def test_search_with_lesson_filter(self):
        """Test search with lesson number filter"""
        mock_results = SearchResults(
            documents=["Lesson specific content"],
            metadata=[{"course_title": "Data Science", "lesson_number": 5}],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson5"
        
        result = self.search_tool.execute("pandas", lesson_number=5)
        
        self.mock_vector_store.search.assert_called_once_with(
            query="pandas",
            course_name=None,
            lesson_number=5
        )
        
        self.assertIn("[Data Science - Lesson 5]", result)
    
    def test_search_with_both_filters(self):
        """Test search with both course name and lesson number"""
        mock_results = SearchResults(
            documents=["Very specific content"],
            metadata=[{"course_title": "Machine Learning", "lesson_number": 2}],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.return_value = "https://example.com/ml-lesson2"
        
        result = self.search_tool.execute("neural networks", course_name="Machine Learning", lesson_number=2)
        
        self.mock_vector_store.search.assert_called_once_with(
            query="neural networks",
            course_name="Machine Learning",
            lesson_number=2
        )
    
    def test_empty_search_results(self):
        """Test handling of empty search results"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.search_tool.execute("nonexistent topic")
        
        self.assertEqual(result, "No relevant content found.")
    
    def test_empty_results_with_course_filter(self):
        """Test empty results with course filter"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.search_tool.execute("topic", course_name="Nonexistent Course")
        
        self.assertEqual(result, "No relevant content found in course 'Nonexistent Course'.")
    
    def test_empty_results_with_lesson_filter(self):
        """Test empty results with lesson filter"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.search_tool.execute("topic", lesson_number=99)
        
        self.assertEqual(result, "No relevant content found in lesson 99.")
    
    def test_empty_results_with_both_filters(self):
        """Test empty results with both filters"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.search_tool.execute("topic", course_name="Test Course", lesson_number=1)
        
        self.assertEqual(result, "No relevant content found in course 'Test Course' in lesson 1.")
    
    def test_search_error_handling(self):
        """Test handling of search errors"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Database connection failed"
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.search_tool.execute("any query")
        
        self.assertEqual(result, "Database connection failed")
    
    def test_sources_tracking(self):
        """Test that sources are properly tracked"""
        mock_results = SearchResults(
            documents=["Content 1", "Content 2"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": None}
            ],
            distances=[0.1, 0.2],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.side_effect = ["https://link1.com", None]
        
        self.search_tool.execute("test query")
        
        # Check that sources were tracked correctly
        expected_sources = [
            {"text": "Course A - Lesson 1", "link": "https://link1.com"},
            {"text": "Course B", "link": None}
        ]
        self.assertEqual(self.search_tool.last_sources, expected_sources)
    
    def test_lesson_link_error_handling(self):
        """Test handling of lesson link retrieval errors"""
        mock_results = SearchResults(
            documents=["Content with link error"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.side_effect = Exception("Link retrieval failed")
        
        # Should not raise exception, should handle gracefully
        with patch('builtins.print') as mock_print:
            result = self.search_tool.execute("test")
            
        # Verify warning was printed
        mock_print.assert_called_once()
        self.assertIn("Warning:", mock_print.call_args[0][0])
        
        # Result should still be formatted properly
        self.assertIn("[Test Course - Lesson 1]", result)
    
    def test_metadata_without_lesson_number(self):
        """Test handling metadata without lesson number"""
        mock_results = SearchResults(
            documents=["Course overview content"],
            metadata=[{"course_title": "Overview Course"}],  # No lesson_number
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.search_tool.execute("overview")
        
        # Should format without lesson number
        self.assertIn("[Overview Course]", result)
        self.assertNotIn("Lesson", result)
    
    def test_tool_definition(self):
        """Test that tool definition is properly structured"""
        definition = self.search_tool.get_tool_definition()
        
        self.assertEqual(definition["name"], "search_course_content")
        self.assertIn("description", definition)
        self.assertIn("input_schema", definition)
        
        # Check required fields
        required = definition["input_schema"]["required"]
        self.assertIn("query", required)
        self.assertNotIn("course_name", required)  # Should be optional
        self.assertNotIn("lesson_number", required)  # Should be optional
        
        # Check properties
        properties = definition["input_schema"]["properties"]
        self.assertIn("query", properties)
        self.assertIn("course_name", properties)
        self.assertIn("lesson_number", properties)


if __name__ == '__main__':
    unittest.main()