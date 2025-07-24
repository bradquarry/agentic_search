#!/usr/bin/env python3
"""
Enhanced Flask backend with four search experiences:
1. Semantic Search (AI-powered with OpenAI summary)
2. Keyword Search (Multi-match lexical search)
3. Date Browse (All reviews by date)
4. Agentic AI (Automatic pros/cons extraction with personalized recommendations)

Usage: python3 appv2.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime
import time
from openai import OpenAI

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes

# Elasticsearch configuration
ES_URL = "https://f5-logs-demo.es.us-east-2.aws.elastic-cloud.com:9243"
ES_API_KEY = "S2t0OExwZ0JOaDhIaVRqOS1yS2M6b01TUWZVMDNPMUs1Nm9mMm40cWg2dw=="

# OpenAI configuration
OPENAI_API_KEY = "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"
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Default user (in production, this would come from auth)
DEFAULT_USER = "Student2025"

# Logging
def log_request(endpoint, method, data=None):
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] {method} {endpoint}")
    if data:
        print(f"  Data: {json.dumps(data, indent=2)}")

def transform_review_data(hit):
    """Transform Elasticsearch hit to frontend-expected format"""
    source = hit['_source']
    return {
        'id': hit['_id'],
        'date': source.get('date'),
        'username': source.get('username'),
        'location': source.get('location'),
        'product_description': source.get('product'),  # Map product -> product_description
        'stars': source.get('stars'),
        'title': source.get('title'),
        'description': source.get('review_text'),  # Map review_text -> description
        'helpful_count': source.get('helpful_votes', 0),  # Map helpful_votes -> helpful_count
        'verified_purchase': source.get('verified', False),  # Map verified -> verified_purchase
        'images': []  # No images in new schema
    }

def get_user_profile(username):
    """Fetch user profile from Elasticsearch"""
    try:
        response = requests.get(
            f"{ES_URL}/user_profile/_doc/{username}",
            headers={
                "Authorization": f"ApiKey {ES_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json().get('_source', {})
        else:
            print(f"  User profile not found for {username}")
            return None
            
    except Exception as e:
        print(f"  Error fetching user profile: {str(e)}")
        return None

@app.route('/')
def health_check():
    return jsonify({
        "status": "running",
        "message": "Multi-Search Experience Backend (AI + Keyword + Date Browse + Agentic AI)",
        "search_modes": {
            "ai_search": "Semantic search with OpenAI-powered summaries",
            "keyword_search": "Traditional lexical search using multi-match",
            "date_browse": "All reviews sorted by date (newest first)",
            "agentic_ai": "Automatic pros/cons extraction with personalized recommendations"
        },
        "endpoints": {
            "/search-reviews": "POST - Browse all reviews by date",
            "/semantic-search": "POST - AI-powered semantic search with summary",
            "/keyword-search": "POST - Keyword-based multi-match search",
            "/agentic-summary": "POST - Automatic pros/cons extraction with personalized recommendations",
            "/cluster-health": "GET - Check Elasticsearch health"
        }
    })

@app.route('/cluster-health', methods=['GET'])
def cluster_health():
    """Test Elasticsearch cluster connectivity"""
    try:
        log_request('/cluster-health', 'GET')
        
        response = requests.get(
            f"{ES_URL}/_cluster/health",
            headers={
                "Authorization": f"ApiKey {ES_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        print(f"  ES Response: {response.status_code}")
        
        if response.status_code == 200:
            return jsonify({
                "status": "success",
                "elasticsearch": response.json()
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Elasticsearch returned {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"  Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to connect to Elasticsearch: {str(e)}"
        }), 500

@app.route('/search-reviews', methods=['POST'])
def search_reviews():
    """Get all reviews sorted by latest date (Browse All mode)"""
    try:
        # Default search query - get all reviews sorted by date desc
        es_query = {
            "query": {
                "match_all": {}
            },
            "size": 50,
            "sort": [
                {"date": {"order": "desc"}}
            ]
        }
            
        log_request('/search-reviews', 'POST', es_query)
        
        # Make request to Elasticsearch
        response = requests.post(
            f"{ES_URL}/review_index/_search",
            headers={
                "Authorization": f"ApiKey {ES_API_KEY}",
                "Content-Type": "application/json"
            },
            json=es_query,
            timeout=30
        )
        
        print(f"  ES Response: {response.status_code}")
        
        if response.status_code == 200:
            es_data = response.json()
            
            # Transform response for frontend
            reviews = [transform_review_data(hit) for hit in es_data.get('hits', {}).get('hits', [])]
            
            result = {
                "status": "success",
                "total": es_data.get('hits', {}).get('total', {}).get('value', 0),
                "took": es_data.get('took', 0),
                "reviews": reviews,
                "search_mode": "date_browse"
            }
            
            print(f"  Returned {len(reviews)} reviews (date sorted)")
            return jsonify(result)
            
        else:
            return jsonify({
                "status": "error",
                "message": f"Elasticsearch search failed: {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"  Network Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Network error: {str(e)}"
        }), 500
    except Exception as e:
        print(f"  Server Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/keyword-search', methods=['POST'])
def keyword_search():
    """Perform keyword-based multi-match search on title and review text"""
    try:
        data = request.get_json()
        search_query = data.get('query', '')
        
        if not search_query:
            return jsonify({
                "status": "error",
                "message": "No search query provided"
            }), 400
        
        log_request('/keyword-search', 'POST', {"search_query": search_query})
        
        # Multi-match query on title and review_text fields
        es_query = {
            "query": {
                "multi_match": {
                    "query": search_query,
                    "fields": ["title^2", "review_text"],  # Boost title matches
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "size": 20,
            "sort": [
                {"_score": {"order": "desc"}},  # Sort by relevance first
                {"date": {"order": "desc"}}     # Then by date
            ]
        }
        
        # Search Elasticsearch
        response = requests.post(
            f"{ES_URL}/review_index/_search",
            headers={
                "Authorization": f"ApiKey {ES_API_KEY}",
                "Content-Type": "application/json"
            },
            json=es_query,
            timeout=30
        )
        
        print(f"  ES Response: {response.status_code}")
        
        if response.status_code == 200:
            es_data = response.json()
            hits = es_data.get('hits', {}).get('hits', [])
            
            # Transform response for frontend
            reviews = [transform_review_data(hit) for hit in hits]
            
            result = {
                "status": "success",
                "query": search_query,
                "total": es_data.get('hits', {}).get('total', {}).get('value', 0),
                "took": es_data.get('took', 0),
                "reviews": reviews,
                "search_mode": "keyword",
                "max_score": es_data.get('hits', {}).get('max_score', 0)
            }
            
            print(f"  Found {len(reviews)} reviews matching '{search_query}'")
            return jsonify(result)
            
        else:
            return jsonify({
                "status": "error",
                "message": f"Elasticsearch search failed: {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"  Network Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Network error: {str(e)}"
        }), 500
    except Exception as e:
        print(f"  Server Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/semantic-search', methods=['POST'])
def semantic_search():
    """Perform semantic search and generate OpenAI summary (AI Search mode)"""
    try:
        data = request.get_json()
        search_text = data.get('text', '')
        
        if not search_text:
            return jsonify({
                "status": "error",
                "message": "No search text provided"
            }), 400
        
        log_request('/semantic-search', 'POST', {"search_text": search_text})
        
        # Semantic search query using ELSER on the semantic subfield
        es_query = {
            "query": {
                "semantic": {
                    "field": "review_text.semantic",
                    "query": search_text
                }
            },
            "size": 5,  # Get top 5 results for RAG
            "_source": ["date", "username", "title", "review_text", "stars", "product"]
        }
        
        # Search Elasticsearch
        response = requests.post(
            f"{ES_URL}/review_index/_search",
            headers={
                "Authorization": f"ApiKey {ES_API_KEY}",
                "Content-Type": "application/json"
            },
            json=es_query,
            timeout=30
        )
        
        print(f"  ES Response: {response.status_code}")
        
        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": f"Elasticsearch search failed: {response.status_code}",
                "details": response.text
            }), response.status_code
            
        es_data = response.json()
        hits = es_data.get('hits', {}).get('hits', [])
        
        if not hits:
            return jsonify({
                "status": "success",
                "query": search_text,
                "summary": "No relevant reviews found for your search.",
                "total_results": 0,
                "search_mode": "ai_semantic"
            })
        
        # Prepare context for OpenAI
        review_context = []
        for hit in hits:
            source = hit['_source']
            review_context.append({
                "title": source.get('title', ''),
                "review": source.get('review_text', ''),
                "stars": source.get('stars', 0),
                "product": source.get('product', ''),
                "username": source.get('username', '')
            })
        
        # Generate OpenAI summary
        try:
            # Create context string for OpenAI
            context_text = ""
            for i, review in enumerate(review_context, 1):
                context_text += f"Review {i}:\n"
                context_text += f"Title: {review['title']}\n"
                context_text += f"Rating: {review['stars']}/5 stars\n"
                context_text += f"Product: {review['product']}\n"
                context_text += f"Review: {review['review']}\n"
                context_text += f"By: {review['username']}\n\n"
            
            # OpenAI API call
            openai_response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert assistant that analyzes product reviews. Based on the provided reviews, create a comprehensive summary that addresses the user's search query. Focus on the most relevant insights, common themes, pros/cons, and specific details mentioned in the reviews. Be concise but thorough."
                    },
                    {
                        "role": "user",
                        "content": f"User search query: '{search_text}'\n\nRelevant reviews:\n{context_text}\n\nPlease provide a detailed summary addressing the search query based on these reviews. Include specific insights, common themes, and any notable patterns you observe."
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            ai_summary = openai_response.choices[0].message.content.strip()
            
        except Exception as openai_error:
            print(f"  OpenAI Error: {str(openai_error)}")
            ai_summary = f"Error generating AI summary: {str(openai_error)}"
        
        # Return results
        result = {
            "status": "success",
            "query": search_text,
            "summary": ai_summary,
            "total_results": len(hits),
            "search_score": hits[0].get('_score', 0) if hits else 0,
            "search_mode": "ai_semantic"
        }
        
        print(f"  Generated AI summary for '{search_text}' using {len(hits)} reviews")
        return jsonify(result)
            
    except requests.exceptions.RequestException as e:
        print(f"  Network Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Network error: {str(e)}"
        }), 500
    except Exception as e:
        print(f"  Server Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/agentic-summary', methods=['POST'])
def agentic_summary():
    """Generate automatic pros/cons summary with personalized recommendations (Agentic AI mode)"""
    try:
        start_time = time.time()
        data = request.get_json()
        
        # Get username from request, default to Student2025 if not provided
        username = data.get('username', DEFAULT_USER)
        
        log_request('/agentic-summary', 'POST', {"username": username})
        
        # Get user profile
        user_profile = get_user_profile(username)
        print(f"  Fetched profile for user: {username}")
        
        # Get ALL reviews from Elasticsearch
        es_query = {
            "query": {
                "match_all": {}
            },
            "size": 100,  # Get more reviews for comprehensive analysis
            "_source": ["date", "username", "title", "review_text", "stars", "product"]
        }
        
        # Search Elasticsearch
        response = requests.post(
            f"{ES_URL}/review_index/_search",
            headers={
                "Authorization": f"ApiKey {ES_API_KEY}",
                "Content-Type": "application/json"
            },
            json=es_query,
            timeout=30
        )
        
        print(f"  ES Response: {response.status_code}")
        
        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": f"Elasticsearch search failed: {response.status_code}",
                "details": response.text
            }), response.status_code
            
        es_data = response.json()
        hits = es_data.get('hits', {}).get('hits', [])
        
        if not hits:
            return jsonify({
                "status": "success",
                "pros": ["No reviews available for analysis"],
                "cons": ["No reviews available for analysis"],
                "personalized_recommendation": "Unable to generate recommendation without reviews.",
                "total_reviews_analyzed": 0,
                "processing_time": int((time.time() - start_time) * 1000),
                "search_mode": "agentic_ai",
                "username": username
            })
        
        # Prepare all reviews for OpenAI
        all_reviews_text = ""
        for i, hit in enumerate(hits, 1):
            source = hit['_source']
            all_reviews_text += f"Review {i}:\n"
            all_reviews_text += f"Title: {source.get('title', '')}\n"
            all_reviews_text += f"Rating: {source.get('stars', 0)}/5 stars\n"
            all_reviews_text += f"Review: {source.get('review_text', '')}\n\n"
        
        # Prepare user profile context
        user_context = ""
        if user_profile:
            # Calculate average past purchase price
            past_purchases = user_profile.get('past_purchases', [])
            avg_price = sum([p.get('price', 0) for p in past_purchases]) / len(past_purchases) if past_purchases else 0
            
            user_context = f"""
User Profile:
- Username: {user_profile.get('username')}
- Occupation: {user_profile.get('occupation')}
- Annual Income: ${user_profile.get('annual_income', 0):,}
- Credit Limit: ${user_profile.get('credit_limit', 0):,}
- Past Purchases Average Price: ${avg_price:,.2f}
- Their Own Review: "{user_profile.get('past_reviews', [{}])[0].get('review_text', '')}"
- Price Sensitivity: {user_profile.get('preferences', {}).get('price_sensitivity', 'unknown')}
- Feature Priorities: {', '.join(user_profile.get('preferences', {}).get('feature_priorities', []))}
"""
        
        # Generate OpenAI pros/cons analysis with personalized recommendation
        try:
            # Different prompts based on user profile
            if username == 'TechUser92':
                system_prompt = """You are an expert product analyst and personal shopping advisor. Analyze all the provided reviews and user profile to:
1. Extract EXACTLY 3 main pros and EXACTLY 3 main cons about the Apple Watch Series 10
2. Provide a personalized recommendation based on the user's financial situation and needs

Your response must be in this exact JSON format:
{
    "pros": [
        "First pro point - be specific and mention the feature",
        "Second pro point - be specific and mention the feature",
        "Third pro point - be specific and mention the feature"
    ],
    "cons": [
        "First con point - be specific and mention the issue",
        "Second con point - be specific and mention the issue",
        "Third con point - be specific and mention the issue"
    ],
    "personalized_recommendation": "A detailed recommendation (80-120 words) that acknowledges their tech enthusiasm and disposable income, recommending the highest-end model with all premium features and accessories, explaining why the investment is worth it for their lifestyle and career"
}

Rules:
1. Each pro/con should be a complete sentence (15-25 words)
2. Focus on the most frequently mentioned positives and negatives
3. The personalized recommendation MUST consider the user's high income and low price sensitivity
4. Recommend the most premium options available with all accessories
5. Emphasize cutting-edge features and ecosystem benefits"""
            else:
                # Default prompt for Student2025
                system_prompt = """You are an expert product analyst and personal shopping advisor. Analyze all the provided reviews and user profile to:
1. Extract EXACTLY 3 main pros and EXACTLY 3 main cons about the Apple Watch Series 10
2. Provide a personalized recommendation based on the user's financial situation and needs

Your response must be in this exact JSON format:
{
    "pros": [
        "First pro point - be specific and mention the feature",
        "Second pro point - be specific and mention the feature",
        "Third pro point - be specific and mention the feature"
    ],
    "cons": [
        "First con point - be specific and mention the issue",
        "Second con point - be specific and mention the issue",
        "Third con point - be specific and mention the issue"
    ],
    "personalized_recommendation": "A detailed recommendation (80-120 words) that acknowledges the product quality but recommends a more budget-friendly alternative like the Xiaomi Mi Band 7, Amazfit Band 7, or Fitbit Inspire 3, explaining why it's better for their budget and still meets their core needs"
}

Rules:
1. Each pro/con should be a complete sentence (15-25 words)
2. Focus on the most frequently mentioned positives and negatives
3. The personalized recommendation MUST consider the user's limited budget and recommend a cheaper alternative
4. Be empathetic but direct about the financial reality for a college student
5. Suggest specific alternative products with much lower total cost of ownership"""
            
            openai_response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"{user_context}\n\nAnalyze these {len(hits)} Apple Watch Series 10 reviews and provide pros, cons, and a personalized recommendation:\n\n{all_reviews_text}"
                    }
                ],
                max_tokens=800,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            ai_response = json.loads(openai_response.choices[0].message.content.strip())
            pros = ai_response.get("pros", [])[:3]
            cons = ai_response.get("cons", [])[:3]
            personalized_recommendation = ai_response.get("personalized_recommendation", "")
            
            # Fallback if parsing fails
            if not pros or not cons or not personalized_recommendation:
                raise ValueError("Invalid response format from OpenAI")
            
        except Exception as openai_error:
            print(f"  OpenAI Error: {str(openai_error)}")
            # Fallback pros/cons/recommendation based on user
            if username == 'TechUser92':
                pros = [
                    "Display quality and size improvements make everything more readable",
                    "S10 chip delivers exceptional performance for demanding apps",
                    "Advanced health sensors including temperature and blood oxygen monitoring"
                ]
                cons = [
                    "Battery life still requires daily charging with heavy usage",
                    "Some advanced features require iPhone 15 Pro or newer",
                    "Titanium edition significantly more expensive than aluminum"
                ]
                personalized_recommendation = "For someone with your tech expertise and income, the Apple Watch Series 10 Titanium with Cellular is the perfect choice. The $799 investment delivers cutting-edge health monitoring, seamless ecosystem integration, and premium materials that match your professional image. Add the Milanese Loop ($99) for versatility. The productivity gains alone justify the cost for your $185k salary."
            else:
                pros = [
                    "Display quality and size improvements make everything more readable",
                    "Health tracking features including heart rate and sleep monitoring",
                    "Seamless integration with iPhone and Apple ecosystem"
                ]
                cons = [
                    "Battery life concerns with heavy usage and GPS tracking",
                    "Premium pricing may not justify upgrade from recent models",
                    "Many features require additional subscriptions adding to cost"
                ]
                personalized_recommendation = "While the Apple Watch Series 10 is an excellent device, given your student budget and $500 credit limit, I'd recommend the Xiaomi Mi Band 7 ($50) or Amazfit Band 7 ($50). These alternatives offer essential features you need - step tracking, sleep monitoring, and study timers - without the financial strain. You'll save over $300 and avoid costly subscriptions while still getting reliable fitness tracking for campus life."
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Return results
        result = {
            "status": "success",
            "pros": pros,
            "cons": cons,
            "personalized_recommendation": personalized_recommendation,
            "total_reviews_analyzed": len(hits),
            "processing_time": processing_time,
            "search_mode": "agentic_ai",
            "user_profile_loaded": user_profile is not None,
            "username": username
        }
        
        print(f"  Generated Personalized Agentic AI summary from {len(hits)} reviews for {username} in {processing_time}ms")
        return jsonify(result)
            
    except requests.exceptions.RequestException as e:
        print(f"  Network Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Network error: {str(e)}"
        }), 500
    except Exception as e:
        print(f"  Server Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Multi-Search Experience Backend...")
    print(f"📡 Elasticsearch: {ES_URL}")
    print(f"🤖 OpenAI: Configured for AI summaries")
    print(f"👤 Default User: {DEFAULT_USER}")
    print(f"🌐 Backend will run on: http://localhost:8001")
    print("\n🔍 Search Modes Available:")
    print("  1️⃣  AI Search      - Semantic search + OpenAI summaries")
    print("  2️⃣  Keyword Search - Traditional multi-match lexical search") 
    print("  3️⃣  Browse All     - All reviews by date (no search)")
    print("  4️⃣  Agentic AI     - Personalized pros/cons + budget recommendations")
    print("\n📡 API Endpoints:")
    print("  GET  /                 - Health check & mode info")
    print("  GET  /cluster-health   - Test Elasticsearch connection")
    print("  POST /search-reviews   - Browse all reviews (date sorted)")
    print("  POST /keyword-search   - Multi-match keyword search")
    print("  POST /semantic-search  - AI semantic search + summary")
    print("  POST /agentic-summary  - Personalized pros/cons + recommendations")
    print("\n" + "="*60)
    
    app.run(debug=True, host='0.0.0.0', port=8001)