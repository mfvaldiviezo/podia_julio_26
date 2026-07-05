"""Main routes for the Flask application."""

import os
import csv
import json
from datetime import datetime
from functools import wraps

import pandas as pd
import cv2
import werkzeug.utils
from flask import Response, render_template, jsonify, request, send_file


def create_auth_decorator(app, config):
    """Create authentication decorator for routes."""
    
    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not (auth.username == config.AUTH_USERNAME and 
                               auth.password == config.AUTH_PASSWORD):
                return Response(
                    'Login Required', 
                    401, 
                    {'WWW-Authenticate': 'Basic realm="Login Required"'}
                )
            return f(*args, **kwargs)
        return decorated
    
    return requires_auth


def init_routes(app, state, voice, processor, ml_engine, logger):
    """Initialize all Flask routes."""
    
    # Create auth decorator
    from ..config import Config
    requires_auth = create_auth_decorator(app, Config)
    
    # Import local dependencies
    from ..models.patient_manager import PatientManager
    from ..services.biomechanics import BiomechanicsCalculator
    from ..services.video_processor import VideoProcessor
    
    biomech = BiomechanicsCalculator()
    video_proc = VideoProcessor()
    
    # Anti-cache headers
    @app.after_request
    def add_header(r):
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        return r
    
    # Main dashboard
    @app.route('/')
    @requires_auth
    def index():
        return render_template('dashboard.html')
    
    # Video streaming endpoint
    @app.route('/video_feed')
    @requires_auth
    def video_feed():
        source = request.args.get('src', '0')
        return Response(
            video_proc.generate_frames(source, biomech, processor, state, voice, logger),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    
    # Video upload endpoint
    @app.route('/upload_video', methods=['POST'])
    @requires_auth
    def upload_video():
        if 'video' not in request.files:
            return jsonify({'status': 'error', 'msg': 'No file'})
        
        file = request.files['video']
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if ext not in {'mp4', 'avi', 'mov', 'mkv', 'webm'}:
            return jsonify({'status': 'error', 'msg': 'Invalid format'})
        
        path = os.path.join(Config.UPLOAD_FOLDER, werkzeug.utils.secure_filename(file.filename))
        file.save(path)
        
        # Check duration (max 5 min)
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        
        if fps > 0 and (frames/fps) > 300:
            os.remove(path)
            return jsonify({'status': 'error', 'msg': 'Video too long (max 5 min)'})
        
        return jsonify({'status': 'ok', 'filepath': path})
    
    # Patient management endpoints
    @app.route('/api/patient', methods=['POST'])
    @requires_auth
    def create_patient():
        pid = PatientManager.create_patient(request.json)
        with state.lock:
            state.current_patient_id = pid
        return jsonify({'status': 'ok', 'patient_id': pid})
    
    @app.route('/api/patient/active/<pid>', methods=['PUT'])
    @requires_auth
    def set_active_patient(pid):
        p = PatientManager.get_patient(pid)
        if p:
            with state.lock:
                state.current_patient_id = pid
            return jsonify({'status': 'ok', 'name': p['name']})
        return jsonify({'error': 'Not found'}), 404
    
    @app.route('/api/patient/<pid>', methods=['GET'])
    @requires_auth
    def get_patient_by_id(pid):
        """Get patient data by ID."""
        p = PatientManager.get_patient(pid)
        if p:
            return jsonify(p)
        return jsonify({'error': 'Paciente no encontrado'}), 404
    
    @app.route('/api/patient/<pid>', methods=['DELETE'])
    @requires_auth
    def delete_patient(pid):
        """Delete a patient from the system."""
        if PatientManager.delete_patient(pid):
            with state.lock:
                if state.current_patient_id == pid:
                    state.current_patient_id = None
            logger.info(f"Patient deleted: {pid}")
            return jsonify({'status': 'ok', 'msg': f'Paciente {pid} eliminado'})
        return jsonify({'error': 'Paciente no encontrado'}), 404
    
    # Session management
    @app.route('/api/session/toggle', methods=['POST'])
    @requires_auth
    def toggle_session():
        with state.lock:
            state.session_active = not state.session_active
            if state.session_active:
                state.session_data.clear()
        return jsonify({'status': 'ok', 'active': state.session_active})
    
    @app.route('/api/export_report/<pid>', methods=['GET'])
    @requires_auth
    def export_report(pid):
        with state.lock:
            if state.session_data:
                # Filter by patient if index 11 matches
                p_data = [d[:11] for d in state.session_data 
                         if len(d) > 11 and d[11] == pid]
                if not p_data:
                    p_data = [d[:11] for d in state.session_data]  # Fallback
                
                df = pd.DataFrame(
                    p_data,
                    columns=['RA', 'LA', 'RK', 'LK', 'RH', 'LH', 
                            'RFPA', 'LFPA', 'RArch', 'LArch', 'Sym']
                )
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                path = os.path.join(Config.REPORTS_FOLDER, f'patient_{pid}_{timestamp}.csv')
                df.to_csv(path, index=False)
                return send_file(os.path.abspath(path), as_attachment=True)
        
        return jsonify({'error': 'No data'}), 400
    
    # System status endpoint
    @app.route('/api/status', methods=['GET'])
    @requires_auth
    def sys_status():
        with state.lock:
            return jsonify({
                'status_msg': state.system_status_msg,
                'angles': state.current_live_angles,
                'samples': len(state.ml_labels_buffer),
                'fps': round(state.current_fps, 1),
                'session_active': state.session_active,
                'current_patient': state.current_patient_id
            })
    
    # List all patients
    @app.route('/api/patients', methods=['GET'])
    @requires_auth
    def list_patients():
        patients = PatientManager.list_patients()
        return jsonify(patients)
    
    # Clinical ranges configuration
    @app.route('/api/ranges', methods=['GET', 'PUT'])
    @requires_auth
    def clinical_ranges():
        with state.lock:
            if request.method == 'PUT':
                state.clinical_ranges.update(request.json)
                state.save_state()
                return jsonify({'status': 'ok'})
            return jsonify(state.clinical_ranges)
    
    # Label sample for ML training
    @app.route('/api/label_sample', methods=['POST'])
    @requires_auth
    def label_sample():
        label = request.json.get('label')
        if not label:
            return jsonify({'error': 'No label provided'}), 400
        
        with state.lock:
            if not state.session_data:
                return jsonify({
                    'error': 'No session data to label. Start capture first.'
                }), 400
            
            last_features = state.session_data[-1][:11]
            
            csv_file = os.path.join(Config.LOGS_FOLDER, 'gait_training_data.csv')
            header = ['ra', 'la', 'rk', 'lk', 'rh', 'lh', 
                     'rfpa', 'lfpa', 'rarch', 'larch', 'sym', 'label']
            file_exists = os.path.isfile(csv_file)
            
            with open(csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(header)
                writer.writerow(list(last_features) + [label])
        
        logger.info(f"Sample labeled: {label}")
        return jsonify({'status': 'ok', 'msg': f'Muestra guardada como {label}'})
    
    # Train ML model
    @app.route('/api/train_model', methods=['POST'])
    @requires_auth
    def train_model():
        csv_file = os.path.join(Config.LOGS_FOLDER, 'gait_training_data.csv')
        if not os.path.exists(csv_file):
            return jsonify({
                'error': 'No training database found (logs/gait_training_data.csv)'
            }), 400
        
        try:
            df = pd.read_csv(csv_file)
            if len(df) < 10:
                return jsonify({
                    'error': f'Insufficient samples ({len(df)}/10)'
                }), 400
            
            features = df.iloc[:, :-1].values.tolist()
            labels = df.iloc[:, -1].astype(int).tolist()
            
            success, msg = ml_engine.train_from_buffers(features, labels)
            
            if success:
                # Update state buffers
                with state.lock:
                    state.ml_features_buffer.clear()
                    state.ml_labels_buffer.clear()
                    for f, l in zip(features, labels):
                        state.ml_features_buffer.append(f)
                        state.ml_labels_buffer.append(l)
                
                return jsonify({'status': 'ok', 'msg': msg})
            else:
                return jsonify({'error': msg}), 400
                
        except Exception as e:
            logger.error(f"Training error: {e}")
            return jsonify({'error': str(e)}), 500
    
    return app
