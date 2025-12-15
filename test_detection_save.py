"""
Test script to verify detection saving to database
"""
import asyncio
import os
from dotenv import load_dotenv
from uuid import UUID

# Load environment variables
load_dotenv()

async def test_detection_save():
    """Test saving a detection to the database"""
    from app.core.database import AsyncSessionLocal
    from app.crud.analytics import analytics
    from app.schemas.analytics import DetectionCreate

    try:
        # Create a test detection
        test_feed_id = "0232f27a-c103-40d7-a3c9-0ef7d746f87a"  # Use your actual feed ID

        detection_data = DetectionCreate(
            feed_id=UUID(test_feed_id),
            detection_type="test_anomaly",
            confidence=0.85,
            description="Test detection to verify database saving works",
            bounding_box=None,
            metadata={
                "test": True,
                "risk_level": "high"
            },
            frame_id="test_frame_999"
        )

        print(f"Creating test detection for feed: {test_feed_id}")
        print(f"Detection data: {detection_data}")

        async with AsyncSessionLocal() as db:
            result = await analytics.create_detection(db, obj_in=detection_data)
            print(f"✅ SUCCESS! Detection saved with ID: {result.id}")
            print(f"   Type: {result.detection_type}")
            print(f"   Confidence: {result.confidence}")
            print(f"   Timestamp: {result.timestamp}")
            return result

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("Testing detection save to database...")
    print("=" * 50)
    result = asyncio.run(test_detection_save())
    if result:
        print("\n✅ Test PASSED - Detection saving works!")
    else:
        print("\n❌ Test FAILED - Check errors above")

