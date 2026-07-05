"""Clinical test routes for balance and heel-raise assessments."""

import os
import json
import time
import uuid
from datetime import datetime
from functools import wraps

import numpy as np
import scipy.stats as st
from flask import Response, jsonify, request


def create_test_routes(app, state, logger):
    """Initialize clinical test routes."""
    
    from ..config import Config
    
    # Create auth decorator
    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not (auth.username == Config.AUTH_USERNAME and 
                               auth.password == Config.AUTH_PASSWORD):
                return Response(
                    'Login Required', 
                    401, 
                    {'WWW-Authenticate': 'Basic realm="Login Required"'}
                )
            return f(*args, **kwargs)
        return decorated
    
    @app.route('/api/test/balance/start', methods=['POST'])
    @requires_auth
    def start_balance_test():
        """Start monopodal balance test - configure temporary state."""
        test_config = request.json or {}
        with state.lock:
            state.test_mode = {
                'type': 'balance',
                'active': True,
                'start_time': time.time(),
                'duration_sec': test_config.get('duration', 10),
                'support_leg': test_config.get('leg', 'right'),
                'samples': []
            }
        logger.info(f"Balance test started: {state.test_mode}")
        return jsonify({'status': 'ok', 'test_id': str(uuid.uuid4())[:6]})
    
    @app.route('/api/test/balance/stop', methods=['POST'])
    @requires_auth
    def stop_balance_test():
        """Stop test and calculate final metrics."""
        with state.lock:
            if not state.test_mode or state.test_mode['type'] != 'balance':
                return jsonify({'error': 'No active balance test'}), 400
            
            samples = state.test_mode.get('samples', [])
            if len(samples) < 5:
                state.test_mode = None
                return jsonify({'error': 'Insufficient data for analysis'}), 400
            
            # Extract support ankle coordinates
            leg_key = 'r_ankle' if state.test_mode['support_leg'] == 'right' else 'l_ankle'
            x_vals = [s.get(leg_key, {}).get('x', 0) for s in samples]
            y_vals = [s.get(leg_key, {}).get('y', 0) for s in samples]
            
            # Calculate oscillations (std dev as stability proxy)
            lateral_osc = st.tstd(x_vals) * 100
            ap_osc = st.tstd(y_vals) * 100
            total_osc = np.sqrt(lateral_osc**2 + ap_osc**2)
            
            # Severity classification
            if total_osc < 5:
                stability = ('Estable', 'green', '✅ Control postural adecuado')
            elif total_osc < 15:
                stability = ('Moderado', 'orange', '⚠️ Oscilación dentro de límites aceptables')
            else:
                stability = ('Inestable', 'red', '❌ Requiere intervención/rehabilitación')
            
            # Calculate 95% confidence radius
            confidence_radius = 1.96 * total_osc
            
            result = {
                'duration_sec': round(time.time() - state.test_mode['start_time'], 1),
                'samples_analyzed': len(samples),
                'oscillation': {
                    'lateral_deg': round(lateral_osc, 2),
                    'ap_deg': round(ap_osc, 2),
                    'total_deg': round(total_osc, 2)
                },
                'confidence_radius_deg': round(confidence_radius, 2),
                'stability': {
                    'level': stability[0],
                    'color': stability[1],
                    'message': stability[2]
                }
            }
            
            # Save to patient session log
            if state.current_patient_id:
                result_record = {
                    'timestamp': datetime.now().isoformat(),
                    'test_type': 'balance_monopodal',
                    'leg': state.test_mode['support_leg'],
                    'result': result
                }
                log_path = os.path.join(
                    Config.LOGS_FOLDER, 
                    f'patient_{state.current_patient_id}_tests.json'
                )
                
                logs = []
                if os.path.exists(log_path):
                    try:
                        with open(log_path, 'r', encoding='utf-8') as f:
                            logs = json.load(f)
                    except (json.JSONDecodeError, IOError):
                        logs = []
                
                logs.append(result_record)
                try:
                    with open(log_path, 'w', encoding='utf-8') as f:
                        json.dump(logs, f, ensure_ascii=False, indent=2)
                except IOError as e:
                    logger.error(f"Failed to save test results: {e}")
            
            state.test_mode = None
            return jsonify({'status': 'ok', 'result': result})
    
    @app.route('/api/test/heelraise/start', methods=['POST'])
    @requires_auth
    def start_heelraise_test():
        """Start heel-raise counter for dynamic dorsiflexion assessment."""
        config = request.json or {}
        with state.lock:
            state.test_mode = {
                'type': 'heelraise',
                'active': True,
                'leg': config.get('leg', 'both'),  # 'right', 'left', or 'both'
                'repetitions': {'right': 0, 'left': 0},
                'max_dorsiflexion': {'right': [], 'left': []},
                'phase': 'neutral',
                'debounce_ms': config.get('debounce', 500),
                'min_dorsiflexion': config.get('min_angle', 30),
                'last_peak_time': 0
            }
        logger.info(f"Heel-raise test started: {state.test_mode}")
        return jsonify({'status': 'ok'})
    
    @app.route('/api/test/heelraise/stop', methods=['POST'])
    @requires_auth
    def stop_heelraise_test():
        """Stop heel-raise test and return repetition count."""
        with state.lock:
            if not state.test_mode or state.test_mode['type'] != 'heelraise':
                return jsonify({'error': 'No active heel-raise test'}), 400
            
            result = {
                'repetitions': state.test_mode['repetitions'].copy(),
                'max_dorsiflexion': {
                    'right': max(state.test_mode['max_dorsiflexion']['right']) 
                             if state.test_mode['max_dorsiflexion']['right'] else 0,
                    'left': max(state.test_mode['max_dorsiflexion']['left']) 
                            if state.test_mode['max_dorsiflexion']['left'] else 0
                }
            }
            
            # Save to patient log
            if state.current_patient_id:
                result_record = {
                    'timestamp': datetime.now().isoformat(),
                    'test_type': 'heel_raise',
                    'result': result
                }
                log_path = os.path.join(
                    Config.LOGS_FOLDER,
                    f'patient_{state.current_patient_id}_tests.json'
                )
                
                logs = []
                if os.path.exists(log_path):
                    try:
                        with open(log_path, 'r', encoding='utf-8') as f:
                            logs = json.load(f)
                    except (json.JSONDecodeError, IOError):
                        logs = []
                
                logs.append(result_record)
                try:
                    with open(log_path, 'w', encoding='utf-8') as f:
                        json.dump(logs, f, ensure_ascii=False, indent=2)
                except IOError as e:
                    logger.error(f"Failed to save test results: {e}")
            
            state.test_mode = None
            return jsonify({'status': 'ok', 'result': result})
    
    @app.route('/api/patient/<pid>/timeline', methods=['GET'])
    @requires_auth
    def get_patient_timeline(pid):
        """Get chronological history of tests for a patient."""
        log_path = os.path.join(Config.LOGS_FOLDER, f'patient_{pid}_tests.json')
        
        if not os.path.exists(log_path):
            return jsonify([])
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                timeline = json.load(f)
            # Sort by timestamp
            timeline.sort(key=lambda x: x.get('timestamp', ''))
            return jsonify(timeline)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading patient timeline: {e}")
            return jsonify([])
    
    return app
