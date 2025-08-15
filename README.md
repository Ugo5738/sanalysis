# Analysis API Documentation

This documentation describes the endpoints available in the Analysis API service. The API provides functionality for managing properties, property images, and analysis tasks.

## Base URL

```
/api/v1/analysis/
```

## Authentication

Most endpoints require authentication. Include your authentication token in the request header:

```
Authorization: Bearer <your_token>
```

## Endpoints

### Properties

#### List Properties

```http
GET /properties/
```

Returns a list of properties associated with the authenticated user's phone number.

**Response**: `200 OK`

```json
[
  {
    "id": "string",
    "url": "string",
    "address": "string",
    "price": "string",
    "bedrooms": "integer",
    "bathrooms": "integer",
    "size": "string",
    "house_type": "string",
    "agent": "string",
    "description": "string",
    "reviewed_description": "string",
    "listing_type": "string",
    "time_on_market": "string",
    "features": "array",
    "image_urls": "array",
    "floorplan_urls": "array",
    "overall_analysis": "string",
    "created_at": "datetime"
  }
]
```

#### Analyze Property

```http
POST /properties/analyze/
```

Initiates an analysis task for a property.

**Request Body**:

```json
{
  "property_id": "string",
  "super_id": "string",
  "phone_number": "string",
  "job_id": "string",
  "source": "string" // optional, defaults to "frontend"
}
```

**Response**: `202 Accepted`

```json
{
  "super_id": "string",
  "property_id": "string"
}
```

#### Get Analysis Status

```http
GET /properties/{property_id}/analysis_status/
```

Returns the status of the latest analysis task for a property.

**Response**: `200 OK`

```json
{
  "id": "string",
  "status": "string",
  "progress": "integer",
  "stage": "string",
  "stage_progress": "object"
}
```

#### Get Shared Property View

```http
GET /properties/{property_id}/shared/{share_token}/
```

Public endpoint to access shared property information.

**Response**: `200 OK`

```json
{
  "property_url": "string",
  "address": "string",
  "price": "string",
  "bedrooms": "integer",
  "bathrooms": "integer",
  "size": "string",
  "house_type": "string",
  "agent": "string",
  "description": "string",
  "reviewed_description": "string",
  "listing_type": "string",
  "time_on_market": "string",
  "features": "array",
  "image_urls": "array",
  "floorplan_urls": "array",
  "overall_analysis": "string",
  "stages": "object"
}
```

#### Get Analysis Results

```http
GET /properties/{property_id}/results/
```

Returns the complete analysis results for a property.

**Response**: `200 OK` or `202 Accepted`

```json
{
  "property_url": "string",
  "address": "string",
  "price": "string",
  // ... same fields as shared view ...
  "stages": "object"
}
```

### Property Images

#### Upload Property Images

```http
POST /property-images/
```

Upload one or multiple images for a property.

**Request Body**: `multipart/form-data`

```
property: string (property_id)
images: file[] (multiple files allowed)
```

**Response**: `201 Created`

```json
[
  {
    "id": "string",
    "property": "string",
    "image": "string" (URL)
  }
]
```

### Prompts

#### Update Prompt

```http
POST /update-prompt/
```

Creates a new version of a prompt and marks it as active.

**Request Body**:

```json
{
  "name": "string",
  "content": "string"
}
```

**Response**: `200 OK`

```json
{
  "message": "string"
}
```

#### Get Prompt

```http
GET /get-prompt/?name={prompt_name}
```

Retrieves the active version of a specific prompt.

**Response**: `200 OK`

```json
{
  "name": "string",
  "content": "string",
  "version": "integer",
  "is_active": "boolean"
}
```

## Error Responses

The API uses standard HTTP status codes:

- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Invalid share token or insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses follow this format:

```json
{
  "error": "Error message description"
}
```
