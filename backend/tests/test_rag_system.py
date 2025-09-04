import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Tuple

# Add the parent directory to sys.path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system import RAGSystem
from models import Course, Lesson, CourseChunk


class MockConfig:
    """Mock configuration for testing"""

    def __init__(self):
        self.CHUNK_SIZE = 800
        self.CHUNK_OVERLAP = 100
        self.CHROMA_PATH = "test_chroma"
        self.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        self.MAX_RESULTS = 5
        self.ANTHROPIC_API_KEY = "test_api_key"
        self.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
        self.MAX_HISTORY = 2


class TestRAGSystem(unittest.TestCase):
    """Test suite for RAG system content-query handling"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = MockConfig()

        # Mock all the component classes to avoid actual initialization
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
            patch("rag_system.ToolManager"),
            patch("rag_system.CourseSearchTool"),
            patch("rag_system.CourseOutlineTool"),
        ):

            self.rag_system = RAGSystem(self.config)

        # Set up mocks for testing
        self.setup_mocks()

    def setup_mocks(self):
        """Setup mock objects for components"""
        self.rag_system.ai_generator = Mock()
        self.rag_system.tool_manager = Mock()
        self.rag_system.session_manager = Mock()
        self.rag_system.vector_store = Mock()
        self.rag_system.document_processor = Mock()

    def test_query_without_session(self):
        """Test query processing without session ID"""
        # Setup mocks
        self.rag_system.ai_generator.generate_response.return_value = (
            "AI response about Python"
        )
        self.rag_system.tool_manager.get_tool_definitions.return_value = [
            {"name": "search_course_content"}
        ]
        self.rag_system.tool_manager.get_last_sources.return_value = [
            {"text": "Python Basics - Lesson 1", "link": "https://example.com/lesson1"}
        ]

        # Execute query
        response, sources = self.rag_system.query("What is Python?")

        # Verify AI generator was called correctly
        self.rag_system.ai_generator.generate_response.assert_called_once()
        call_args = self.rag_system.ai_generator.generate_response.call_args

        # Check query parameter
        self.assertEqual(
            call_args.kwargs["query"],
            "Answer this question about course materials: What is Python?",
        )

        # Check conversation history is None
        self.assertIsNone(call_args.kwargs["conversation_history"])

        # Check tools were provided
        self.assertEqual(call_args.kwargs["tools"], [{"name": "search_course_content"}])
        self.assertEqual(call_args.kwargs["tool_manager"], self.rag_system.tool_manager)

        # Verify session manager was not used
        self.rag_system.session_manager.get_conversation_history.assert_not_called()
        self.rag_system.session_manager.add_exchange.assert_not_called()

        # Verify sources management
        self.rag_system.tool_manager.get_last_sources.assert_called_once()
        self.rag_system.tool_manager.reset_sources.assert_called_once()

        # Check return values
        self.assertEqual(response, "AI response about Python")
        self.assertEqual(
            sources,
            [
                {
                    "text": "Python Basics - Lesson 1",
                    "link": "https://example.com/lesson1",
                }
            ],
        )

    def test_query_with_session(self):
        """Test query processing with session ID"""
        session_id = "user_session_123"

        # Setup mocks
        self.rag_system.session_manager.get_conversation_history.return_value = (
            "Previous conversation context"
        )
        self.rag_system.ai_generator.generate_response.return_value = (
            "Contextual AI response"
        )
        self.rag_system.tool_manager.get_tool_definitions.return_value = []
        self.rag_system.tool_manager.get_last_sources.return_value = []

        # Execute query
        response, sources = self.rag_system.query(
            "Follow up question", session_id=session_id
        )

        # Verify session history was retrieved
        self.rag_system.session_manager.get_conversation_history.assert_called_once_with(
            session_id
        )

        # Verify conversation history was passed to AI
        call_args = self.rag_system.ai_generator.generate_response.call_args
        self.assertEqual(
            call_args.kwargs["conversation_history"], "Previous conversation context"
        )

        # Verify session was updated
        self.rag_system.session_manager.add_exchange.assert_called_once_with(
            session_id, "Follow up question", "Contextual AI response"
        )

    def test_query_with_tool_execution(self):
        """Test query that results in tool execution"""
        # Setup mocks to simulate tool usage
        self.rag_system.ai_generator.generate_response.return_value = (
            "Based on my search, Python is a programming language."
        )
        self.rag_system.tool_manager.get_tool_definitions.return_value = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            }
        ]
        self.rag_system.tool_manager.get_last_sources.return_value = [
            {
                "text": "Python Programming - Lesson 2",
                "link": "https://example.com/python2",
            },
            {
                "text": "Advanced Python - Lesson 1",
                "link": "https://example.com/advanced1",
            },
        ]

        response, sources = self.rag_system.query("Tell me about Python programming")

        # Verify tool definitions were retrieved and provided
        self.rag_system.tool_manager.get_tool_definitions.assert_called_once()

        # Verify sources were retrieved and reset
        self.rag_system.tool_manager.get_last_sources.assert_called_once()
        self.rag_system.tool_manager.reset_sources.assert_called_once()

        # Check that sources were returned
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]["text"], "Python Programming - Lesson 2")
        self.assertEqual(sources[1]["link"], "https://example.com/advanced1")

    def test_query_prompt_formatting(self):
        """Test that query is properly formatted as a prompt"""
        test_queries = [
            "What is machine learning?",
            "How do I use pandas?",
            "Explain neural networks",
        ]

        for query in test_queries:
            self.rag_system.ai_generator.generate_response.return_value = (
                "Test response"
            )
            self.rag_system.tool_manager.get_tool_definitions.return_value = []
            self.rag_system.tool_manager.get_last_sources.return_value = []

            self.rag_system.query(query)

            # Verify prompt formatting
            call_args = self.rag_system.ai_generator.generate_response.call_args
            expected_prompt = f"Answer this question about course materials: {query}"
            self.assertEqual(call_args.kwargs["query"], expected_prompt)

    def test_empty_sources_handling(self):
        """Test handling when no sources are returned"""
        self.rag_system.ai_generator.generate_response.return_value = (
            "General knowledge response"
        )
        self.rag_system.tool_manager.get_tool_definitions.return_value = []
        self.rag_system.tool_manager.get_last_sources.return_value = []

        response, sources = self.rag_system.query("General knowledge question")

        # Should return empty sources list
        self.assertEqual(sources, [])
        self.assertEqual(response, "General knowledge response")

    def test_add_course_document_success(self):
        """Test successful course document addition"""
        # Setup mock course and chunks
        mock_course = Course(
            title="Test Course",
            instructor="Test Instructor",
            lessons=[Lesson(lesson_number=1, title="Lesson 1")],
        )
        mock_chunks = [
            CourseChunk(
                content="Chunk 1",
                course_title="Test Course",
                lesson_number=1,
                chunk_index=0,
            ),
            CourseChunk(
                content="Chunk 2",
                course_title="Test Course",
                lesson_number=1,
                chunk_index=1,
            ),
        ]

        self.rag_system.document_processor.process_course_document.return_value = (
            mock_course,
            mock_chunks,
        )

        # Execute
        course, chunk_count = self.rag_system.add_course_document("/path/to/course.txt")

        # Verify document processing
        self.rag_system.document_processor.process_course_document.assert_called_once_with(
            "/path/to/course.txt"
        )

        # Verify vector store operations
        self.rag_system.vector_store.add_course_metadata.assert_called_once_with(
            mock_course
        )
        self.rag_system.vector_store.add_course_content.assert_called_once_with(
            mock_chunks
        )

        # Check return values
        self.assertEqual(course, mock_course)
        self.assertEqual(chunk_count, 2)

    def test_add_course_document_error_handling(self):
        """Test error handling in course document addition"""
        # Setup to raise exception
        self.rag_system.document_processor.process_course_document.side_effect = (
            Exception("Processing failed")
        )

        with patch("builtins.print") as mock_print:
            course, chunk_count = self.rag_system.add_course_document(
                "/path/to/bad_course.txt"
            )

        # Should handle error gracefully
        self.assertIsNone(course)
        self.assertEqual(chunk_count, 0)

        # Verify error was logged
        mock_print.assert_called_once()
        self.assertIn("Error processing course document", mock_print.call_args[0][0])

    def test_add_course_folder_with_clear_existing(self):
        """Test adding course folder with clear existing option"""
        with (
            patch("os.path.exists", return_value=True),
            patch(
                "os.listdir", return_value=["course1.txt", "course2.pdf", "ignored.log"]
            ),
            patch("os.path.isfile", return_value=True),
        ):

            # Setup mock responses
            mock_course1 = Course(title="Course 1", lessons=[])
            mock_course2 = Course(title="Course 2", lessons=[])
            mock_chunks1 = [
                CourseChunk(content="Chunk", course_title="Course 1", chunk_index=0)
            ]
            mock_chunks2 = [
                CourseChunk(content="Chunk", course_title="Course 2", chunk_index=0)
            ]

            self.rag_system.document_processor.process_course_document.side_effect = [
                (mock_course1, mock_chunks1),
                (mock_course2, mock_chunks2),
            ]
            self.rag_system.vector_store.get_existing_course_titles.return_value = []

            # Execute with clear_existing=True
            courses, chunks = self.rag_system.add_course_folder(
                "/path/to/courses", clear_existing=True
            )

            # Verify data was cleared
            self.rag_system.vector_store.clear_all_data.assert_called_once()

            # Should process 2 files (txt and pdf, not log)
            self.assertEqual(
                self.rag_system.document_processor.process_course_document.call_count, 2
            )

            # Check return values
            self.assertEqual(courses, 2)
            self.assertEqual(chunks, 2)

    def test_add_course_folder_skip_existing(self):
        """Test that existing courses are skipped"""
        with (
            patch("os.path.exists", return_value=True),
            patch("os.listdir", return_value=["existing_course.txt", "new_course.txt"]),
            patch("os.path.isfile", return_value=True),
        ):

            # Setup mocks - first course exists, second is new
            existing_course = Course(title="Existing Course", lessons=[])
            new_course = Course(title="New Course", lessons=[])

            self.rag_system.document_processor.process_course_document.side_effect = [
                (existing_course, []),
                (
                    new_course,
                    [
                        CourseChunk(
                            content="New", course_title="New Course", chunk_index=0
                        )
                    ],
                ),
            ]
            self.rag_system.vector_store.get_existing_course_titles.return_value = [
                "Existing Course"
            ]

            with patch("builtins.print") as mock_print:
                courses, chunks = self.rag_system.add_course_folder("/path/to/courses")

            # Should only add new course
            self.assertEqual(courses, 1)  # Only new course added
            self.assertEqual(chunks, 1)  # Only chunks from new course

            # Verify existing course was skipped
            mock_print.assert_any_call(
                "Course already exists: Existing Course - skipping"
            )

    def test_get_course_analytics(self):
        """Test course analytics retrieval"""
        self.rag_system.vector_store.get_course_count.return_value = 3
        self.rag_system.vector_store.get_existing_course_titles.return_value = [
            "Course A",
            "Course B",
            "Course C",
        ]

        analytics = self.rag_system.get_course_analytics()

        expected = {
            "total_courses": 3,
            "course_titles": ["Course A", "Course B", "Course C"],
        }
        self.assertEqual(analytics, expected)

    def test_integration_query_flow(self):
        """Test the complete query flow integration"""
        session_id = "test_session"

        # Setup realistic mock responses
        self.rag_system.session_manager.get_conversation_history.return_value = (
            "User: Hi\nAssistant: Hello!"
        )
        self.rag_system.tool_manager.get_tool_definitions.return_value = [
            {"name": "search_course_content", "description": "Search courses"}
        ]
        self.rag_system.ai_generator.generate_response.return_value = (
            "Python is a versatile programming language."
        )
        self.rag_system.tool_manager.get_last_sources.return_value = [
            {"text": "Python Fundamentals", "link": "https://course.com/python"}
        ]

        # Execute complete flow
        response, sources = self.rag_system.query(
            "What is Python?", session_id=session_id
        )

        # Verify complete integration
        # 1. Session history retrieved
        self.rag_system.session_manager.get_conversation_history.assert_called_once_with(
            session_id
        )

        # 2. AI generator called with all parameters
        ai_call_args = self.rag_system.ai_generator.generate_response.call_args
        self.assertEqual(
            ai_call_args.kwargs["query"],
            "Answer this question about course materials: What is Python?",
        )
        self.assertEqual(
            ai_call_args.kwargs["conversation_history"], "User: Hi\nAssistant: Hello!"
        )
        self.assertEqual(
            ai_call_args.kwargs["tools"],
            [{"name": "search_course_content", "description": "Search courses"}],
        )
        self.assertEqual(
            ai_call_args.kwargs["tool_manager"], self.rag_system.tool_manager
        )

        # 3. Sources retrieved and reset
        self.rag_system.tool_manager.get_last_sources.assert_called_once()
        self.rag_system.tool_manager.reset_sources.assert_called_once()

        # 4. Session updated
        self.rag_system.session_manager.add_exchange.assert_called_once_with(
            session_id, "What is Python?", "Python is a versatile programming language."
        )

        # 5. Correct return values
        self.assertEqual(response, "Python is a versatile programming language.")
        self.assertEqual(
            sources,
            [{"text": "Python Fundamentals", "link": "https://course.com/python"}],
        )


if __name__ == "__main__":
    unittest.main()
