"""
Unit tests for the batch processor module.
"""
import pytest
import asyncio
import os
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from batch_processor import BatchProcessor


@pytest.fixture
def batch_processor():
    """Create a BatchProcessor instance for testing."""
    processor = BatchProcessor(
        mongodb_uri="mongodb://localhost:27017",
        batch_size=5,
        max_concurrent=3,
        batch_dir="test_batch_files"
    )
    # Create test directory for batch files
    os.makedirs(processor.batch_dir, exist_ok=True)
    yield processor
    # Cleanup test files - recursively remove directories
    def remove_dir_recursively(path):
        if os.path.exists(path):
            for entry in os.listdir(path):
                entry_path = os.path.join(path, entry)
                if os.path.isdir(entry_path):
                    remove_dir_recursively(entry_path)
                else:
                    try:
                        os.remove(entry_path)
                    except (PermissionError, OSError) as e:
                        print(f"Warning: Could not remove file {entry_path}: {e}")
            try:
                os.rmdir(path)
            except (PermissionError, OSError) as e:
                print(f"Warning: Could not remove directory {path}: {e}")
    
    # Try to clean up the test directory
    try:
        remove_dir_recursively(processor.batch_dir)
    except Exception as e:
        print(f"Warning: Failed to clean up test directory: {e}")


@pytest.fixture
def mock_mongo_client():
    """Create a mock MongoDB client."""
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = AsyncMock()
    mock_client.get_unprocessed_documents = AsyncMock(return_value=(
        [{"_id": "doc1", "query": "Test query 1"}, {"_id": "doc2", "query": "Test query 2"}],
        True,
        "doc2"
    ))
    mock_client.store_classification = AsyncMock()
    mock_client.mark_as_processed = AsyncMock()
    return mock_client


class TestBatchProcessor:
    """Test suite for the BatchProcessor class."""
    
    @pytest.mark.asyncio
    async def test_connect(self, batch_processor, mock_mongo_client):
        """Test connecting to MongoDB."""
        with patch('batch_processor.MongoClient', return_value=mock_mongo_client):
            result = await batch_processor.connect()
            
            assert result is True
            mock_mongo_client.connect.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_connect_error(self, batch_processor):
        """Test error handling when connecting to MongoDB."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('batch_processor.MongoClient', return_value=mock_client):
            result = await batch_processor.connect()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_fetch_unprocessed_queries(self, batch_processor, mock_mongo_client):
        """Test fetching unprocessed queries from MongoDB."""
        # Setup the batch processor with mock client
        batch_processor.mongo_client = mock_mongo_client
        
        # Test the method
        documents, more_available = await batch_processor.fetch_unprocessed_queries()
        
        # Check the result
        assert len(documents) == 2
        assert more_available is True
        assert batch_processor.last_processed_id == "doc2"
        mock_mongo_client.get_unprocessed_documents.assert_called_once_with(
            batch_size=batch_processor.batch_size,
            last_id=None
        )
    
    @pytest.mark.asyncio
    async def test_fetch_unprocessed_queries_with_last_id(self, batch_processor, mock_mongo_client):
        """Test fetching unprocessed queries with a last_id."""
        # Setup the batch processor with mock client
        batch_processor.mongo_client = mock_mongo_client
        batch_processor.last_processed_id = "last_doc"
        
        # Test the method
        documents, more_available = await batch_processor.fetch_unprocessed_queries()
        
        # Check the result
        mock_mongo_client.get_unprocessed_documents.assert_called_once_with(
            batch_size=batch_processor.batch_size,
            last_id="last_doc"
        )
    
    @pytest.mark.asyncio
    async def test_fetch_unprocessed_queries_error(self, batch_processor, mock_mongo_client):
        """Test error handling when fetching unprocessed queries."""
        # Setup the batch processor with mock client
        batch_processor.mongo_client = mock_mongo_client
        mock_mongo_client.get_unprocessed_documents.side_effect = Exception("Database error")
        
        # Test the method
        documents, more_available = await batch_processor.fetch_unprocessed_queries()
        
        assert documents == []
        assert more_available is False
    
    @pytest.mark.asyncio
    async def test_prepare_message(self, batch_processor):
        """Test message preparation for LLM."""
        query = "How do I reset my password?"
        message = batch_processor._prepare_message(query)
        
        assert isinstance(message, list)
        assert len(message) == 1
        assert message[0]["role"] == "user"
        assert query in message[0]["content"]
    
    @pytest.mark.asyncio
    async def test_process_document_success(self, batch_processor, mock_mongo_client):
        """Test successful document processing."""
        # Set up the batch processor with our mock client
        batch_processor.mongo_client = mock_mongo_client
        
        # Create test document
        doc = {"_id": "test_id", "query": "How do I reset my password?"}
        
        # Mock the LLM classification with a successful response
        mock_classification = {
            "intent": "help",
            "topic": "account",
            "sentiment": "neutral"
        }
        
        with patch('batch_processor.safe_ollama_classify_async', AsyncMock(return_value=mock_classification)):
            result = await batch_processor._process_document(doc)
            
            assert result["status"] == "success"
            assert result["retried"] is False
            mock_mongo_client.store_classification.assert_called_once()
            mock_mongo_client.mark_as_processed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_document_with_retry(self, batch_processor, mock_mongo_client):
        """Test document processing with retry."""
        # Set up the batch processor with our mock client
        batch_processor.mongo_client = mock_mongo_client
        
        # Create test document
        doc = {"_id": "test_id", "query": "How do I reset my password?"}
        
        # Mock the LLM classification with error then success
        mock_error = {"error": "LLM temporarily unavailable"}
        mock_success = {"intent": "help", "topic": "account", "sentiment": "neutral"}
        
        with patch('batch_processor.safe_ollama_classify_async', 
                   AsyncMock(side_effect=[mock_error, mock_success])):
            result = await batch_processor._process_document(doc)
            
            assert result["status"] == "success"
            assert result["retried"] is True
            mock_mongo_client.store_classification.assert_called_once()
            mock_mongo_client.mark_as_processed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_document_no_query(self, batch_processor, mock_mongo_client):
        """Test document processing with no query field."""
        # Set up the batch processor with our mock client
        batch_processor.mongo_client = mock_mongo_client
        
        # Create test document with no query
        doc = {"_id": "test_id"}
        
        result = await batch_processor._process_document(doc)
        
        assert result["status"] == "failure"
        mock_mongo_client.mark_as_processed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_document_llm_error(self, batch_processor, mock_mongo_client):
        """Test document processing with LLM error that exceeds max retries."""
        # Set up the batch processor with our mock client
        batch_processor.mongo_client = mock_mongo_client
        batch_processor.max_retries = 2
        
        # Create test document
        doc = {"_id": "test_id", "query": "How do I reset my password?"}
        
        # Mock the LLM classification with persistent errors
        mock_error = {"error": "LLM classification failed"}
        
        with patch('batch_processor.safe_ollama_classify_async', 
                  AsyncMock(return_value=mock_error)):
            result = await batch_processor._process_document(doc)
            
            assert result["status"] == "failure"
            assert result["retried"] is True
            mock_mongo_client.mark_as_processed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_classification(self, batch_processor, mock_mongo_client):
        """Test storing classification result."""
        # Set up the batch processor with our mock client
        batch_processor.mongo_client = mock_mongo_client
        
        # Create test classification
        classification = {
            "document_id": "test_id",
            "query": "How do I reset my password?",
            "intent": "help",
            "topic": "account",
            "sentiment": "neutral",
            "processed_at": datetime.now(timezone.utc)
        }
        
        result = await batch_processor._store_classification(classification)
        
        assert result is True
        mock_mongo_client.store_classification.assert_called_once_with(classification)
    
    @pytest.mark.asyncio
    async def test_mark_as_processed(self, batch_processor, mock_mongo_client):
        """Test marking a document as processed."""
        # Set up the batch processor with our mock client
        batch_processor.mongo_client = mock_mongo_client
        
        # Test marking as processed
        doc_id = "test_id"
        result_data = {"status": "processed"}
        
        with patch('batch_processor.datetime') as mock_datetime:
            # Mock datetime to return a fixed value
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = await batch_processor._mark_as_processed(doc_id, result_data)
            
            assert result is True
            mock_mongo_client.mark_as_processed.assert_called_once_with(doc_id, {
                "processed": True,
                "processed_at": mock_now,
                "processing_result": result_data
            })
    
    @pytest.mark.asyncio
    async def test_process_batch(self, batch_processor):
        """Test processing a batch of documents."""
        # Create test documents
        documents = [
            {"_id": f"doc{i}", "query": f"Test query {i}"} for i in range(3)
        ]
        
        # Mock _process_document to return success for all documents
        mock_results = [
            {"status": "success", "retried": False, "doc_id": f"doc{i}"} 
            for i in range(3)
        ]
        
        with patch.object(batch_processor, '_process_document', 
                          AsyncMock(side_effect=mock_results)) as mock_process:
            batch_stats = await batch_processor.process_batch(documents)
            
            assert mock_process.call_count == 3
            assert batch_stats["total"] == 3
            assert batch_stats["successful"] == 3
            assert batch_stats["failed"] == 0
            assert batch_stats["retried"] == 0
            assert "duration_seconds" in batch_stats
    
    @pytest.mark.asyncio
    async def test_process_batch_mixed_results(self, batch_processor):
        """Test processing a batch with mixed success/failure."""
        # Create test documents
        documents = [
            {"_id": f"doc{i}", "query": f"Test query {i}"} for i in range(4)
        ]
        
        # Mock _process_document to return different results
        mock_results = [
            {"status": "success", "retried": False, "doc_id": "doc0"},
            {"status": "failure", "retried": True, "doc_id": "doc1"},
            {"status": "success", "retried": True, "doc_id": "doc2"},
            {"status": "success", "retried": False, "doc_id": "doc3"},
        ]
        
        with patch.object(batch_processor, '_process_document', 
                          AsyncMock(side_effect=mock_results)) as mock_process:
            batch_stats = await batch_processor.process_batch(documents)
            
            assert mock_process.call_count == 4
            assert batch_stats["total"] == 4
            assert batch_stats["successful"] == 3
            assert batch_stats["failed"] == 1
            assert batch_stats["retried"] == 2
    
    @pytest.mark.asyncio
    async def test_checkpoint_operations(self, batch_processor):
        """Test checkpoint save and load operations."""
        # Setup test data
        batch_processor.last_processed_id = "test_last_id"
        batch_processor.stats = {
            "job_id": batch_processor.job_id,
            "documents_processed": 10,
            "successful": 8,
            "failed": 2,
            "start_time": datetime.now(timezone.utc)
        }
        
        # Mock the batch_file_manager to track save_checkpoint calls
        with patch.object(batch_processor.batch_file_manager, 'save_checkpoint') as mock_save:
            # Test saving checkpoint
            result = await batch_processor.save_checkpoint()
            
            # Verify checkpoint was saved
            assert result is True
            mock_save.assert_called_once()
            
            # Mock checkpoint loading
            checkpoint_data = {
                "last_processed_id": "test_last_id",
                "stats": {
                    "job_id": batch_processor.job_id,
                    "documents_processed": 10,
                    "successful": 8,
                    "failed": 2
                }
            }
            
            # Modify data to test loading
            batch_processor.last_processed_id = None
            batch_processor.stats = {
                "job_id": batch_processor.job_id,
                "documents_processed": 0,
                "successful": 0,
                "failed": 0
            }
            
            # Mock load_checkpoint to return our test data
            with patch.object(batch_processor.batch_file_manager, 'load_checkpoint', 
                              return_value=checkpoint_data):
                # Test loading checkpoint
                result = await batch_processor.load_checkpoint()
                assert result is True
                assert batch_processor.last_processed_id == "test_last_id"
                assert batch_processor.stats["documents_processed"] == 10
    
    @pytest.mark.asyncio
    async def test_process_retry_queue(self, batch_processor, mock_mongo_client):
        """Test processing the retry queue."""
        # Set up the batch processor with our mock client
        batch_processor.mongo_client = mock_mongo_client
        
        # Mock the retry queue
        store_items = {"doc1": {"document_id": "doc1", "query": "Test query"}}
        mark_items = {"doc2": {"processed": True}}
        
        with patch.object(batch_processor.batch_file_manager, 'get_retry_queue_items',
                          side_effect=[store_items, mark_items]) as mock_get_items:
            with patch.object(batch_processor.batch_file_manager, 'remove_from_retry_queue',
                              return_value=True) as mock_remove:
                
                retry_stats = await batch_processor.process_retry_queue()
                
                assert retry_stats["retried"] == 2
                assert retry_stats["successful"] == 2
                assert retry_stats["failed"] == 0
                assert mock_get_items.call_count == 2
                assert mock_remove.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_batch_mode(self, batch_processor, mock_mongo_client):
        """Test running the batch processor in batch mode."""
        # Reset batch processor stats
        batch_processor.stats = {
            "job_id": batch_processor.job_id,
            "documents_processed": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "batches_processed": 0,
            "start_time": None,
            "duration_seconds": 0,
            "processing_rate": 0
        }
        
        # Setup the batch processor with mock client
        with patch('batch_processor.MongoClient', return_value=mock_mongo_client):
            # Mock the fetch_unprocessed_queries method
            with patch.object(batch_processor, 'fetch_unprocessed_queries', 
                              side_effect=[
                                  ([{"_id": "doc1", "query": "test"}], True),
                                  ([{"_id": "doc2", "query": "test2"}], False)
                              ]) as mock_fetch:
                
                # Create a real process_batch method to update stats correctly
                original_process_batch = batch_processor.process_batch
                
                async def mock_process_batch_with_stats(documents):
                    # Return the mock results but also update stats like the real method would
                    batch_processor.stats["batches_processed"] += 1
                    return {"total": 1, "successful": 1, "failed": 0, "retried": 0}
                
                with patch.object(batch_processor, 'process_batch',
                                  side_effect=mock_process_batch_with_stats) as mock_process:
                    with patch.object(batch_processor, 'save_checkpoint',
                                      AsyncMock()) as mock_save:
                        
                        # Run the processor in batch mode
                        stats = await batch_processor.run()
                        
                        # Check results
                        assert mock_fetch.call_count == 2
                        assert mock_process.call_count == 2
                        assert stats["batches_processed"] == 2
                        assert mock_save.call_count >= 1  # At least once for final checkpoint
    
    @pytest.mark.asyncio
    async def test_run_continuous_mode(self, batch_processor, mock_mongo_client):
        """Test running the batch processor in continuous mode."""
        # Setup the batch processor with mock client
        batch_processor.mode = "continuous"
        batch_processor.continuous_interval = 0.1  # Fast for testing
        
        # Mock asyncio.sleep to avoid actual waiting
        async def mock_sleep(seconds):
            # After first sleep, raise CancelledError to end the loop
            raise asyncio.CancelledError()
            
        with patch('batch_processor.MongoClient', return_value=mock_mongo_client):
            with patch.object(batch_processor, 'fetch_unprocessed_queries',
                              return_value=([], False)) as mock_fetch:
                with patch.object(batch_processor, 'process_retry_queue',
                                  AsyncMock()) as mock_retry:
                    with patch('asyncio.sleep', mock_sleep):
                        
                        # Run in continuous mode until CancelledError
                        try:
                            await batch_processor.run(continuous=True)
                        except asyncio.CancelledError:
                            pass
                            
                        # Verify behavior
                        assert mock_fetch.call_count >= 1
                        mock_retry.assert_not_called()  # No retry since we did no batches
                        
    @pytest.mark.asyncio
    async def test_run_recover_mode(self, batch_processor, mock_mongo_client):
        """Test running with recovery from checkpoint."""
        # Setup the batch processor with mock client
        with patch('batch_processor.MongoClient', return_value=mock_mongo_client):
            with patch.object(batch_processor, 'load_checkpoint',
                              AsyncMock(return_value=True)) as mock_load:
                with patch.object(batch_processor, 'process_retry_queue',
                                  AsyncMock()) as mock_retry:
                    with patch.object(batch_processor, 'fetch_unprocessed_queries',
                                      return_value=([], False)) as mock_fetch:
                        
                        # Run with recovery
                        await batch_processor.run(recover=True)
                        
                        # Verify behavior
                        mock_load.assert_called_once()
                        mock_retry.assert_called_once()
                        mock_fetch.assert_called_once()