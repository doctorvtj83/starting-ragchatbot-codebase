"""
API endpoint tests for the RAG system FastAPI application
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import httpx

# Import the app components but create a test version
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import QueryRequest, QueryResponse, CourseStats
from rag_system import RAGSystem
from config import config


def create_test_app():
    """Create a test FastAPI app without static file mounting"""
    app = FastAPI(title="Test Course Materials RAG System")
    
    # Add middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Mock RAG system for testing
    mock_rag_system = Mock(spec=RAGSystem)
    mock_rag_system.session_manager = Mock()
    
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Test endpoint for query processing"""
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Test endpoint for course statistics"""
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/")
    async def root():
        """Test root endpoint"""
        return {"message": "Course Materials RAG System API"}
    
    # Store mock for access in tests
    app.state.mock_rag_system = mock_rag_system
    
    return app


@pytest.fixture
def test_app():
    """Test FastAPI application fixture"""
    return create_test_app()


@pytest.fixture
def client(test_app):
    """Test client fixture"""
    return TestClient(test_app)


@pytest.fixture
def async_client(test_app):
    """Async test client fixture"""
    # Use HTTPX's async client with the test app
    return httpx.AsyncClient(base_url="http://testserver")


class TestAPIEndpoints:
    """Test suite for API endpoints"""
    
    @pytest.mark.api
    def test_root_endpoint(self, client):
        """Test the root endpoint returns expected response"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Course Materials RAG System API"}
    
    @pytest.mark.api
    def test_query_endpoint_success(self, client, test_app, sample_query_response):
        """Test successful query endpoint"""
        # Setup mock responses
        mock_rag = test_app.state.mock_rag_system
        mock_rag.session_manager.create_session.return_value = "test-session-id"
        mock_rag.query.return_value = (
            sample_query_response["answer"], 
            sample_query_response["sources"]
        )
        
        # Test request
        request_data = {
            "query": "What are the key concepts?",
            "session_id": "test-session-id"
        }
        
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "answer" in response_data
        assert "sources" in response_data  
        assert "session_id" in response_data
        assert response_data["session_id"] == "test-session-id"
    
    @pytest.mark.api  
    def test_query_endpoint_no_session_id(self, client, test_app, sample_query_response):
        """Test query endpoint creates session when none provided"""
        # Setup mock responses
        mock_rag = test_app.state.mock_rag_system
        mock_rag.session_manager.create_session.return_value = "new-session-id"
        mock_rag.query.return_value = (
            sample_query_response["answer"],
            sample_query_response["sources"]
        )
        
        # Test request without session_id
        request_data = {
            "query": "What are the key concepts?"
        }
        
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["session_id"] == "new-session-id"
        mock_rag.session_manager.create_session.assert_called_once()
    
    @pytest.mark.api
    def test_query_endpoint_invalid_request(self, client):
        """Test query endpoint with invalid request data"""
        # Missing required 'query' field
        request_data = {
            "session_id": "test-session-id"
        }
        
        response = client.post("/api/query", json=request_data)
        assert response.status_code == 422  # Unprocessable Entity
    
    @pytest.mark.api
    def test_query_endpoint_server_error(self, client, test_app):
        """Test query endpoint handles server errors"""
        # Setup mock to raise exception
        mock_rag = test_app.state.mock_rag_system
        mock_rag.session_manager.create_session.return_value = "test-session-id"
        mock_rag.query.side_effect = Exception("Database connection failed")
        
        request_data = {
            "query": "What are the key concepts?",
            "session_id": "test-session-id"
        }
        
        response = client.post("/api/query", json=request_data)
        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]
    
    @pytest.mark.api
    def test_courses_endpoint_success(self, client, test_app, sample_course_stats):
        """Test successful courses endpoint"""
        # Setup mock response
        mock_rag = test_app.state.mock_rag_system
        mock_rag.get_course_analytics.return_value = sample_course_stats
        
        response = client.get("/api/courses")
        
        assert response.status_code == 200
        response_data = response.json()
        assert "total_courses" in response_data
        assert "course_titles" in response_data
        assert response_data["total_courses"] == 1
        assert response_data["course_titles"] == ["Test Course"]
    
    @pytest.mark.api
    def test_courses_endpoint_server_error(self, client, test_app):
        """Test courses endpoint handles server errors"""
        # Setup mock to raise exception
        mock_rag = test_app.state.mock_rag_system
        mock_rag.get_course_analytics.side_effect = Exception("Analytics service unavailable")
        
        response = client.get("/api/courses")
        assert response.status_code == 500
        assert "Analytics service unavailable" in response.json()["detail"]
    
    @pytest.mark.api
    def test_query_endpoint_empty_query(self, client, test_app):
        """Test query endpoint with empty query string"""
        mock_rag = test_app.state.mock_rag_system
        mock_rag.session_manager.create_session.return_value = "test-session-id"
        mock_rag.query.return_value = ("I need more information to help you.", [])
        
        request_data = {
            "query": "",
            "session_id": "test-session-id"
        }
        
        response = client.post("/api/query", json=request_data)
        assert response.status_code == 200
        # Should still process empty queries
        response_data = response.json()
        assert "answer" in response_data
    
    @pytest.mark.api
    def test_query_endpoint_very_long_query(self, client, test_app):
        """Test query endpoint with very long query"""
        mock_rag = test_app.state.mock_rag_system
        mock_rag.session_manager.create_session.return_value = "test-session-id"
        mock_rag.query.return_value = ("Here's a summary response", [])
        
        # Create a very long query
        long_query = "What are the key concepts? " * 1000
        
        request_data = {
            "query": long_query,
            "session_id": "test-session-id"
        }
        
        response = client.post("/api/query", json=request_data)
        assert response.status_code == 200
        # Should handle long queries gracefully


# Note: Async endpoint testing can be complex with FastAPI TestClient
# The TestClient already handles async endpoints properly, so separate async testing 
# is not strictly necessary for this use case


class TestAPIValidation:
    """Test suite for API request/response validation"""
    
    @pytest.mark.api
    def test_query_request_validation(self, client):
        """Test QueryRequest model validation"""
        # Test with invalid JSON structure
        response = client.post("/api/query", json={"invalid": "data"})
        assert response.status_code == 422
        
        # Test with wrong data types
        response = client.post("/api/query", json={"query": 123})
        assert response.status_code == 422
    
    @pytest.mark.api
    def test_query_response_structure(self, client, test_app):
        """Test QueryResponse structure matches expected format"""
        mock_rag = test_app.state.mock_rag_system
        mock_rag.session_manager.create_session.return_value = "test-session-id"
        mock_rag.query.return_value = (
            "Test answer",
            [{"course_title": "Test", "content": "test content"}]
        )
        
        request_data = {"query": "test"}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data
            
        # Verify data types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)
    
    @pytest.mark.api  
    def test_courses_response_structure(self, client, test_app):
        """Test CourseStats response structure"""
        mock_rag = test_app.state.mock_rag_system
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Course 1", "Course 2"]
        }
        
        response = client.get("/api/courses")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["total_courses", "course_titles"]
        for field in required_fields:
            assert field in data
            
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert all(isinstance(title, str) for title in data["course_titles"])