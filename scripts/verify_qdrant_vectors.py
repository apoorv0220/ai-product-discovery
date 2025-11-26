"""
Quick script to verify if vectors are actually stored in Qdrant points.

Usage:
    python scripts/verify_qdrant_vectors.py [--merchant-id MERCHANT_ID]
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend directories to path
script_dir = Path(__file__).parent
backend_dir = script_dir.parent / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "search-service"))

# Load .env if exists
try:
    from dotenv import load_dotenv
    env_path = script_dir.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from core.qdrant_client import QdrantManager
from shared.config.qdrant import QDRANT_CONFIG

async def verify_vectors(merchant_id: int = 1):
    """Verify if vectors are stored in Qdrant points"""
    print(f"Verifying vectors for merchant {merchant_id}...")
    print("=" * 60)
    
    qm = QdrantManager(url=QDRANT_CONFIG["url"], api_key=QDRANT_CONFIG["api_key"])
    await qm.initialize()
    
    try:
        # Get collection info
        info = await qm.get_collection_info(merchant_id)
        if not info:
            print(f"❌ Collection not found for merchant {merchant_id}")
            return
        
        print(f"Collection: {info.get('name', 'N/A')}")
        print(f"Points Count: {info.get('points_count', 0)}")
        print(f"Indexed Vectors: {info.get('indexed_vectors_count', 0)}")
        print(f"Status: {info.get('status', 'N/A')}")
        print()
        
        # Try to get a sample point with vector
        collection_name = qm._get_collection_name(merchant_id)
        
        # Use the client to scroll and get a point with vector
        scroll_result = await asyncio.to_thread(
            qm.client.scroll,
            collection_name=collection_name,
            limit=1,
            with_vectors=True,
            with_payload=True
        )
        
        if scroll_result and len(scroll_result[0]) > 0:
            point = scroll_result[0][0]
            has_vector = point.vector is not None
            
            print(f"Sample Point:")
            print(f"  ID: {point.id}")
            print(f"  Has Vector: {'✅ YES' if has_vector else '❌ NO'}")
            
            if has_vector:
                vector = point.vector
                if isinstance(vector, dict):
                    # Named vector (multiple vectors per point)
                    print(f"  Vector Type: Named vectors")
                    for name, vec in vector.items():
                        print(f"    - {name}: {len(vec)} dimensions")
                elif isinstance(vector, list):
                    print(f"  Vector Dimensions: {len(vector)}")
                    print(f"  Vector Sample (first 5): {vector[:5]}")
                else:
                    print(f"  Vector Type: {type(vector)}")
                
                print()
                print("✅ SUCCESS: Vectors are stored in Qdrant!")
                print("   Semantic search should work.")
            else:
                print()
                print("❌ WARNING: Vectors are NOT stored in points!")
                print("   Embedding generation may have failed.")
                print("   Run: python scripts/generate_product_embeddings.py --merchant-id", merchant_id)
        else:
            print("⚠️  No points found in collection")
            
        # Check collection config
        collection_info = await asyncio.to_thread(qm.client.get_collection, collection_name)
        if collection_info:
            print()
            print(f"Collection Config:")
            print(f"  Vector Size: {collection_info.config.params.vectors.size}")
            print(f"  Distance Metric: {collection_info.config.params.vectors.distance}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await qm.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--merchant-id", type=int, default=1)
    args = parser.parse_args()
    
    asyncio.run(verify_vectors(args.merchant_id))

