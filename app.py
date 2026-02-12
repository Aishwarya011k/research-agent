"""
Flask web application for Research Agent.
Provides a user-friendly interface for web-based research queries.
"""

from flask import Flask, render_template, request, jsonify, send_file
from research_agent import ResearchAgent, ResearchOutput
import json
import os
from datetime import datetime
import threading
import io

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Global research state
research_state = {
    'in_progress': False,
    'current_question': '',
    'progress': 0,
    'status': '',
    'last_result': None,
    'error': None
}

# Initialize research agent
agent = ResearchAgent()


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/research', methods=['POST'])
def api_research():
    """
    Start a research query.
    
    Expected JSON:
    {
        "question": "research question",
        "max_sources": 10 (optional)
    }
    """
    if research_state['in_progress']:
        return jsonify({'success': False, 'error': 'Research already in progress'}), 400
    
    data = request.get_json()
    question = data.get('question', '').strip()
    max_sources = data.get('max_sources', 10)
    
    if not question:
        return jsonify({'success': False, 'error': 'Question cannot be empty'}), 400
    
    research_state['in_progress'] = True
    research_state['current_question'] = question
    research_state['progress'] = 0
    research_state['status'] = 'Initializing research...'
    research_state['error'] = None
    
    # Run research in background thread
    def run_research():
        try:
            research_state['status'] = 'Planning research steps...'
            research_state['progress'] = 10
            
            research_state['status'] = 'Searching the web...'
            research_state['progress'] = 30
            
            research_state['status'] = 'Extracting key findings...'
            research_state['progress'] = 50
            
            research_state['status'] = 'Synthesizing conclusion...'
            research_state['progress'] = 70
            
            research_state['status'] = 'Evaluating completeness...'
            research_state['progress'] = 85
            
            # Set max sources and run research
            agent.max_sources = max_sources
            output = agent.research(question)
            
            research_state['status'] = 'Formatting results...'
            research_state['progress'] = 95
            
            formatted_output = agent.format_output(output)
            
            research_state['last_result'] = {
                'question': question,
                'output': {
                    'question': output.question,
                    'overview': output.overview,
                    'key_findings': output.key_findings,
                    'challenges': output.challenges,
                    'conclusion': output.conclusion,
                    'sources': output.sources,
                    'essay': output.essay,  # Include generated essay
                    'timestamp': output.timestamp
                },
                'formatted': formatted_output,
                'sources_count': len(agent.memory.notes),
                'avg_credibility': sum(n.reliability_score for n in agent.memory.notes) / len(agent.memory.notes) if agent.memory.notes else 0
            }
            
            research_state['status'] = 'Complete!'
            research_state['progress'] = 100
            
        except Exception as e:
            research_state['error'] = str(e)
            research_state['status'] = f'Error: {str(e)}'
            research_state['in_progress'] = False
        finally:
            research_state['in_progress'] = False
    
    thread = threading.Thread(target=run_research, daemon=True)
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Research started',
        'question': question
    })


@app.route('/api/status', methods=['GET'])
def api_status():
    """Get current research status and API quota."""
    quota = agent.llm_client.get_quota_status()
    return jsonify({
        'in_progress': research_state['in_progress'],
        'progress': research_state['progress'],
        'status': research_state['status'],
        'question': research_state['current_question'],
        'has_result': research_state['last_result'] is not None,
        'error': research_state['error'],
        'quota': quota
    })


@app.route('/api/result', methods=['GET'])
def api_result():
    """Get the last research result."""
    if not research_state['last_result']:
        return jsonify({'success': False, 'error': 'No result available'}), 404
    
    return jsonify({
        'success': True,
        'data': research_state['last_result']
    })


@app.route('/api/history', methods=['GET'])
def api_history():
    """Get list of saved research files."""
    research_dir = 'research_outputs'
    
    if not os.path.exists(research_dir):
        return jsonify({'success': True, 'history': []})
    
    files = []
    for filename in sorted(os.listdir(research_dir), reverse=True)[:20]:
        if filename.endswith('.json'):
            filepath = os.path.join(research_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    files.append({
                        'filename': filename,
                        'question': data.get('question', 'Unknown'),
                        'timestamp': data.get('timestamp', 'Unknown'),
                        'sources_count': len(data.get('notes', []))
                    })
            except:
                pass
    
    return jsonify({'success': True, 'history': files})


@app.route('/api/result/<filename>', methods=['GET'])
def api_result_file(filename):
    """Get a specific research result from file."""
    filepath = os.path.join('research_outputs', filename)
    
    # Safety check
    if not os.path.abspath(filepath).startswith(os.path.abspath('research_outputs')):
        return jsonify({'success': False, 'error': 'Invalid file'}), 404
    
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'File not found'}), 404
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Recreate the formatted output from saved data
        overview = data.get('overview', '')
        question = data.get('question', '')
        key_findings = data.get('key_findings', [])
        challenges = data.get('challenges', [])
        conclusion = data.get('conclusion', '')
        notes = data.get('notes', [])
        
        # Build formatted output (simulation)
        formatted = f"""
{'='*80}
RESEARCH REPORT: {question}
{'='*80}

OVERVIEW:
{overview}

KEY FINDINGS:
"""
        for i, finding in enumerate(key_findings, 1):
            formatted += f"{i}. {finding}\n"
        
        formatted += "\nCONCLUSION:\n" + conclusion
        
        return jsonify({
            'success': True,
            'data': {
                'question': question,
                'overview': overview,
                'key_findings': key_findings,
                'challenges': challenges,
                'conclusion': conclusion,
                'sources_count': len(notes),
                'timestamp': data.get('timestamp', ''),
                'formatted': formatted
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/<format_type>', methods=['GET'])
def api_export(format_type):
    """Export the last result in different formats."""
    if not research_state['last_result']:
        return jsonify({'success': False, 'error': 'No result available'}), 404
    
    result = research_state['last_result']
    
    if format_type == 'json':
        json_str = json.dumps(result['output'], indent=2)
        return send_file(
            io.BytesIO(json_str.encode('utf-8')),
            mimetype='application/json',
            as_attachment=True,
            download_name=f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
    
    elif format_type == 'txt':
        txt_str = result['formatted']
        return send_file(
            io.BytesIO(txt_str.encode('utf-8')),
            mimetype='text/plain',
            as_attachment=True,
            download_name=f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
    
    else:
        return jsonify({'success': False, 'error': 'Invalid format. Use json or txt'}), 400


@app.route('/api/clear', methods=['POST'])
def api_clear():
    """Clear the current research state."""
    research_state['last_result'] = None
    research_state['status'] = ''
    research_state['error'] = None
    
    return jsonify({'success': True, 'message': 'Research cleared'})


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'agent_ready': True
    })


if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════════════════╗
    ║                      RESEARCH AGENT WEB INTERFACE                      ║
    ╚════════════════════════════════════════════════════════════════════════╝
    
    Starting Flask web server...
    
    Open your browser and go to:
    ➜ http://localhost:5000
    
    Press CTRL+C to stop the server.
    """)
    
    app.run(debug=True, port=5000)
