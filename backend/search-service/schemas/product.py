"""
AI Product Discovery Suite - Product Data Schemas

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union


class ProductStock(BaseModel):
    """Stock information for a product"""
    qty: float = Field(default=0, description="Stock quantity")
    is_in_stock: bool = Field(default=True, description="Whether product is in stock")
    manage_stock: Optional[bool] = Field(default=None, description="Whether stock is managed")
    
    class Config:
        extra = "allow"  # Allow additional stock fields from Magento


class ProductAttributes(BaseModel):
    """Product attributes (color, size, etc.)"""
    type: Optional[str] = Field(default=None, description="Product type")
    weight: Optional[float] = Field(default=None, description="Product weight")
    manufacturer: Optional[str] = Field(default=None, description="Manufacturer/brand")
    color: Optional[str] = Field(default=None, description="Color")
    size: Optional[str] = Field(default=None, description="Size")
    material: Optional[str] = Field(default=None, description="Material")
    
    class Config:
        extra = "allow"  # Allow additional attributes from Magento


class ProductData(BaseModel):
    """
    Complete product data schema for validation
    
    This schema validates product data received from various sources
    (Magento module, API calls, etc.) and ensures data integrity
    """
    
    # ===== Required Fields =====
    id: Union[int, str] = Field(..., description="Product ID (required)")
    sku: str = Field(..., min_length=1, description="Product SKU (required)")
    name: str = Field(..., min_length=1, description="Product name (required)")
    
    # ===== Optional but Important Fields =====
    description: Optional[str] = Field(default=None, description="Full product description")
    short_description: Optional[str] = Field(default=None, description="Short description")
    
    # Pricing
    price: float = Field(default=0.0, ge=0, description="Regular price")
    special_price: Optional[float] = Field(default=None, ge=0, description="Special/sale price")
    final_price: Optional[float] = Field(default=None, ge=0, description="Final calculated price")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code")
    
    # Media
    url: Optional[str] = Field(default=None, description="Product URL path")
    image_url: Optional[str] = Field(default=None, description="Product image URL")
    
    # Categorization
    categories: Union[List[int], List[str], List[Any]] = Field(
        default_factory=list, 
        description="Category IDs or names"
    )
    brand: Optional[str] = Field(default=None, description="Brand name")
    
    # Stock
    stock: Optional[Union[ProductStock, Dict[str, Any], bool]] = Field(
        default=None,
        description="Stock information (can be object, dict, or boolean)"
    )
    
    # Attributes
    attributes: Union[ProductAttributes, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Custom product attributes"
    )
    
    # Status and Visibility
    status: int = Field(default=1, description="Product status (1=enabled, 2=disabled)")
    visibility: int = Field(default=4, description="Product visibility (1-4)")
    
    # Platform-specific Context (Optional - for platform integrations)
    store_id: Optional[Union[int, str]] = Field(default=None, description="Platform-specific store identifier")
    website_id: Optional[Union[int, str]] = Field(default=None, description="Platform-specific website identifier")
    
    # Metadata
    version: Optional[int] = Field(default=1, description="Document version")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    
    @validator('id')
    def validate_id(cls, v):
        """Ensure ID is always a string"""
        return str(v) if v is not None else v
    
    @validator('price', 'special_price', 'final_price')
    def validate_prices(cls, v):
        """Ensure prices are non-negative"""
        if v is not None and v < 0:
            return 0
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        """Ensure currency is uppercase"""
        return v.upper() if v else "USD"
    
    @validator('sku', 'name')
    def validate_required_strings(cls, v):
        """Ensure required string fields are not empty"""
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("Field cannot be empty")
        return v.strip() if isinstance(v, str) else v
    
    class Config:
        extra = "allow"  # Allow additional fields from various sources


class DataQualityMetrics(BaseModel):
    """Metrics for assessing product data quality"""
    total_products: int = Field(..., description="Total number of products")
    products_with_price: int = Field(default=0, description="Products with price > 0")
    products_with_image: int = Field(default=0, description="Products with image URL")
    products_with_categories: int = Field(default=0, description="Products with categories")
    products_with_description: int = Field(default=0, description="Products with description")
    completeness_score: float = Field(default=0.0, ge=0, le=100, description="Overall completeness % (0-100)")
    
    def calculate_completeness(self):
        """Calculate overall completeness score"""
        if self.total_products == 0:
            self.completeness_score = 0.0
            return
        
        # Weight different fields by importance
        weights = {
            'price': 0.35,
            'image': 0.25,
            'categories': 0.20,
            'description': 0.20
        }
        
        scores = {
            'price': (self.products_with_price / self.total_products) * 100,
            'image': (self.products_with_image / self.total_products) * 100,
            'categories': (self.products_with_categories / self.total_products) * 100,
            'description': (self.products_with_description / self.total_products) * 100,
        }
        
        weighted_score = sum(scores[field] * weight for field, weight in weights.items())
        self.completeness_score = round(weighted_score, 2)


class IndexResponseEnhanced(BaseModel):
    """Enhanced index response with data quality metrics"""
    success: bool = Field(..., description="Whether indexing succeeded")
    indexed_count: int = Field(..., description="Number of products indexed")
    failed_count: int = Field(default=0, description="Number of products that failed")
    message: str = Field(..., description="Status message")
    data_quality: Optional[DataQualityMetrics] = Field(default=None, description="Data quality metrics")
    validation_errors: Optional[List[str]] = Field(default_factory=list, description="Validation errors")


def validate_product_data(product: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate product data against schema
    
    Args:
        product: Product data dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ProductData(**product)
        return True, None
    except Exception as e:
        return False, str(e)


def calculate_data_quality(products: List[Dict[str, Any]]) -> DataQualityMetrics:
    """
    Calculate data quality metrics for a list of products
    
    Args:
        products: List of product dictionaries
        
    Returns:
        DataQualityMetrics object
    """
    if not products:
        return DataQualityMetrics(total_products=0)
    
    metrics = DataQualityMetrics(
        total_products=len(products),
        products_with_price=sum(1 for p in products if p.get('price', 0) > 0),
        products_with_image=sum(1 for p in products if p.get('image_url')),
        products_with_categories=sum(1 for p in products if p.get('categories')),
        products_with_description=sum(1 for p in products if p.get('description'))
    )
    
    metrics.calculate_completeness()
    return metrics

