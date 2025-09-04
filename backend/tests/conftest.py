"""
Shared test fixtures for the RAG system tests
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from pathlib import Path
from typing import Dict, Any, List

# Import required modules for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from models import Course, Lesson, CourseChunk


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = Mock(spec=Config)
    config.chunk_size = 800
    config.chunk_overlap = 100
    config.max_results = 5
    config.max_history = 2
    config.anthropic_api_key = "test-key"
    config.anthropic_model = "claude-sonnet-4-20250514"
    return config


@pytest.fixture
def sample_course_data():
    """Sample course data for testing"""
    return {
        "title": "Test Course",
        "link": "https://example.com/course",
        "instructor": "Test Instructor",
        "lessons": [
            {
                "title": "Lesson 1: Introduction",
                "link": "https://example.com/lesson1",
                "content": "This is the introduction lesson content with important concepts."
            },
            {
                "title": "Lesson 2: Advanced Topics", 
                "link": "https://example.com/lesson2",
                "content": "This lesson covers advanced topics and practical examples."
            }
        ]
    }


@pytest.fixture
def sample_course(sample_course_data):
    """Sample Course model instance"""
    lessons = [
        Lesson(
            title=lesson["title"],
            link=lesson["link"], 
            content=lesson["content"]
        ) for lesson in sample_course_data["lessons"]
    ]
    
    return Course(
        title=sample_course_data["title"],
        link=sample_course_data["link"],
        instructor=sample_course_data["instructor"],
        lessons=lessons
    )


@pytest.fixture
def sample_course_chunks():
    """Sample course chunks for testing vector operations"""
    return [
        CourseChunk(
            course_title="Test Course",
            course_link="https://example.com/course",
            course_instructor="Test Instructor",
            lesson_title="Lesson 1: Introduction",
            lesson_link="https://example.com/lesson1",
            content="This is the introduction lesson content with important concepts.",
            chunk_index=0
        ),
        CourseChunk(
            course_title="Test Course", 
            course_link="https://example.com/course",
            course_instructor="Test Instructor",
            lesson_title="Lesson 2: Advanced Topics",
            lesson_link="https://example.com/lesson2", 
            content="This lesson covers advanced topics and practical examples.",
            chunk_index=1
        )
    ]


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing"""
    mock_store = Mock()
    mock_store.add_course_chunks = Mock()
    mock_store.add_course_metadata = Mock()
    mock_store.search_content = Mock(return_value=[])
    mock_store.search_courses = Mock(return_value=[])
    mock_store.get_course_count = Mock(return_value=0)
    mock_store.get_all_course_titles = Mock(return_value=[])
    mock_store.clear_collections = Mock()
    return mock_store


@pytest.fixture
def mock_document_processor():
    """Mock document processor for testing"""
    mock_processor = Mock()
    mock_processor.process_file = Mock()
    mock_processor.process_folder = Mock(return_value=([], []))
    return mock_processor


@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing"""
    mock_manager = Mock()
    mock_manager.create_session = Mock(return_value="test-session-id")
    mock_manager.add_to_history = Mock()
    mock_manager.get_history = Mock(return_value=[])
    mock_manager.clear_session = Mock()
    return mock_manager


@pytest.fixture
def mock_ai_generator():
    """Mock AI generator for testing"""
    mock_generator = AsyncMock()
    mock_generator.generate_response = AsyncMock(return_value="Test response")
    return mock_generator


@pytest.fixture
def temporary_docs_folder():
    """Create a temporary folder with sample document files for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create sample course file
        course_file = Path(temp_dir) / "test_course.txt"
        course_content = """Course Title: Test Course
Course Link: https://example.com/course
Course Instructor: Test Instructor

Lesson 1: Introduction
Lesson Link: https://example.com/lesson1
This is the introduction lesson content with important concepts.

Lesson 2: Advanced Topics
Lesson Link: https://example.com/lesson2
This lesson covers advanced topics and practical examples.
"""
        course_file.write_text(course_content)
        yield temp_dir


@pytest.fixture
def sample_query_request():
    """Sample query request data for API testing"""
    return {
        "query": "What are the key concepts covered in the course?",
        "session_id": "test-session-id"
    }


@pytest.fixture
def sample_query_response():
    """Sample query response data for API testing"""
    return {
        "answer": "The course covers introduction and advanced topics with practical examples.",
        "sources": [
            {
                "course_title": "Test Course",
                "lesson_title": "Lesson 1: Introduction",
                "content": "This is the introduction lesson content",
                "course_link": "https://example.com/course",
                "lesson_link": "https://example.com/lesson1"
            }
        ],
        "session_id": "test-session-id"
    }


@pytest.fixture
def sample_course_stats():
    """Sample course statistics for API testing"""
    return {
        "total_courses": 1,
        "course_titles": ["Test Course"]
    }


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing AI generation"""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.content = [Mock(text="Test AI response")]
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically setup test environment for each test"""
    # Ensure we're in the backend directory for imports
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    # Set test environment variables
    os.environ["TESTING"] = "1"
    yield
    
    # Cleanup after test
    if "TESTING" in os.environ:
        del os.environ["TESTING"]