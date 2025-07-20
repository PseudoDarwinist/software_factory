"""
Intelligence API - Project Analysis and Recommendation Endpoints
Provides intelligent insights, recommendations, and trend analysis
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, List
import logging

try:
    from ..services.intelligence_engine import (
        get_intelligence_engine, get_recommendation_engine, get_trend_analyzer
    )
    from ..services.distributed_cache import get_distributed_cache
    from ..models.project import Project
except ImportError:
    from services.intelligence_engine import (
        get_intelligence_engine, get_recommendation_engine, get_trend_analyzer
    )
    from services.distributed_cache import get_distributed_cache
    from models.project import Project

logger = logging.getLogger(__name__)

intelligence_bp = Blueprint('intelligence', __name__, url_prefix='/api/intelligence')


@intelligence_bp.route('/projects/<int:project_id>/analysis', methods=['GET'])
def analyze_project(project_id: int):
    """Get comprehensive analysis for a specific project"""
    try:
        # Check if project exists
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Check cache first
        cache = get_distributed_cache()
        cache_key = f'project_analysis_{project_id}'
        cached_result = cache.get(cache_key, namespace='intelligence')
        
        if cached_result:
            return jsonify({
                'success': True,
                'project_id': project_id,
                'analysis': cached_result,
                'cached': True
            })
        
        # Perform analysis
        analyzer = get_intelligence_engine()
        
        analysis = {
            'complexity': analyzer.analyze_project_complexity(project_id),
            'activity': analyzer.analyze_project_activity(project_id),
            'technologies': analyzer.extract_technology_stack(project_id)
        }
        
        # Cache result for 5 minutes
        cache.set(cache_key, analysis, ttl=300, namespace='intelligence')
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'analysis': analysis,
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Error analyzing project {project_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@intelligence_bp.route('/projects/<int:project_id>/recommendations', methods=['GET'])
def get_project_recommendations(project_id: int):
    """Get intelligent recommendations for a specific project"""
    try:
        # Check if project exists
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Check cache first
        cache = get_distributed_cache()
        cache_key = f'project_recommendations_{project_id}'
        cached_result = cache.get(cache_key, namespace='intelligence')
        
        if cached_result:
            return jsonify({
                'success': True,
                'project_id': project_id,
                'recommendations': cached_result,
                'cached': True
            })
        
        # Generate recommendations
        rec_engine = get_recommendation_engine()
        recommendations = rec_engine.generate_project_recommendations(project_id)
        
        # Convert to dict format
        rec_data = []
        for rec in recommendations:
            rec_data.append({
                'type': rec.recommendation_type,
                'title': rec.title,
                'description': rec.description,
                'target_project_id': rec.target_project_id,
                'confidence': rec.confidence,
                'reasoning': rec.reasoning,
                'metadata': rec.metadata,
                'created_at': rec.created_at.isoformat()
            })
        
        # Cache result for 10 minutes
        cache.set(cache_key, rec_data, ttl=600, namespace='intelligence')
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'recommendations': rec_data,
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Error getting recommendations for project {project_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@intelligence_bp.route('/projects/<int:project_id>/similar', methods=['GET'])
def find_similar_projects(project_id: int):
    """Find projects similar to the specified project"""
    try:
        # Check if project exists
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Get limit from query params
        limit = min(int(request.args.get('limit', 5)), 20)  # Max 20 results
        
        # Check cache first
        cache = get_distributed_cache()
        cache_key = f'similar_projects_{project_id}_{limit}'
        cached_result = cache.get(cache_key, namespace='intelligence')
        
        if cached_result:
            return jsonify({
                'success': True,
                'project_id': project_id,
                'similar_projects': cached_result,
                'cached': True
            })
        
        # Find similar projects
        rec_engine = get_recommendation_engine()
        similar_projects = rec_engine.find_similar_projects(project_id, limit)
        
        # Convert to dict format
        similar_data = []
        for similar in similar_projects:
            similar_data.append({
                'project': {
                    'id': similar['project'].id,
                    'name': similar['project'].name,
                    'description': similar['project'].description,
                    'status': similar['project'].status,
                    'created_at': similar['project'].created_at.isoformat()
                },
                'similarity_score': similar['similarity_score'],
                'common_technologies': similar['common_technologies'],
                'tech_similarity': similar['tech_similarity'],
                'complexity_similarity': similar['complexity_similarity']
            })
        
        # Cache result for 20 minutes
        cache.set(cache_key, similar_data, ttl=1200, namespace='intelligence')
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'similar_projects': similar_data,
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Error finding similar projects for {project_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@intelligence_bp.route('/trends/technologies', methods=['GET'])
def get_technology_trends():
    """Get technology adoption trends"""
    try:
        # Get days parameter
        days = min(int(request.args.get('days', 90)), 365)  # Max 1 year
        
        # Check cache first
        cache = get_distributed_cache()
        cache_key = f'technology_trends_{days}'
        cached_result = cache.get(cache_key, namespace='intelligence')
        
        if cached_result:
            return jsonify({
                'success': True,
                'trends': cached_result,
                'cached': True
            })
        
        # Analyze trends
        trend_analyzer = get_trend_analyzer()
        trends = trend_analyzer.analyze_technology_trends(days)
        
        # Cache result for 30 minutes
        cache.set(cache_key, trends, ttl=1800, namespace='intelligence')
        
        return jsonify({
            'success': True,
            'trends': trends,
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Error getting technology trends: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@intelligence_bp.route('/dashboard', methods=['GET'])
def get_intelligence_dashboard():
    """Get comprehensive intelligence dashboard data"""
    try:
        # Check cache first
        cache = get_distributed_cache()
        cache_key = 'intelligence_dashboard'
        cached_result = cache.get(cache_key, namespace='intelligence')
        
        if cached_result:
            return jsonify({
                'success': True,
                'dashboard': cached_result,
                'cached': True
            })
        
        # Get all projects for overview
        all_projects = Project.query.all()
        
        if not all_projects:
            return jsonify({
                'success': True,
                'dashboard': {
                    'total_projects': 0,
                    'active_projects': 0,
                    'top_technologies': [],
                    'complexity_overview': {},
                    'activity_overview': {}
                },
                'cached': False
            })
        
        # Analyze all projects
        analyzer = get_intelligence_engine()
        trend_analyzer = get_trend_analyzer()
        
        # Get project stats
        active_projects = 0
        complexity_scores = []
        all_technologies = []
        
        for project in all_projects[:10]:  # Limit to first 10 for performance
            activity = analyzer.analyze_project_activity(project.id)
            if activity['activity_level'] != 'dormant':
                active_projects += 1
            
            complexity = analyzer.analyze_project_complexity(project.id)
            complexity_scores.append(complexity['complexity_score'])
            
            technologies = analyzer.extract_technology_stack(project.id)
            all_technologies.extend(technologies)
        
        # Get technology trends
        tech_trends = trend_analyzer.analyze_technology_trends(30)
        
        dashboard_data = {
            'total_projects': len(all_projects),
            'active_projects': active_projects,
            'average_complexity': sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0,
            'top_technologies': tech_trends.get('trends', [])[:5]
        }
        
        # Cache result for 15 minutes
        cache.set(cache_key, dashboard_data, ttl=900, namespace='intelligence')
        
        return jsonify({
            'success': True,
            'dashboard': dashboard_data,
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Error getting intelligence dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500