#!/usr/bin/env python3
"""Serveur local pour cours-enfants — upload de fichiers + commit git automatique.

Usage:
    pip install flask
    python server.py
    → http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import subprocess
import re

app = Flask(__name__)
BASE = Path(__file__).parent

STUDENTS = {
    'assiya': {'folder': 'cm2',  'name': 'Assiya', 'classe': 'CM2'},
    'mayssa': {'folder': '5eme', 'name': 'Mayssa', 'classe': '5ème'},
    'amine':  {'folder': '3eme', 'name': 'Amine',  'classe': '3ème'},
}

ALLOWED_EXT = {'.html', '.pdf'}


def scan():
    data = {}
    for key, info in STUDENTS.items():
        data[key] = {'cours': {}, 'controles': {}}
        for type_ in ('cours', 'controles'):
            d = BASE / info['folder'] / type_
            if d.exists():
                for sd in sorted(d.iterdir()):
                    if sd.is_dir():
                        files = sorted(
                            f.name for f in sd.iterdir()
                            if f.suffix.lower() in ALLOWED_EXT
                        )
                        if files:
                            data[key][type_][sd.name] = files
    # Dossier assiya/ → cours/exercices (fichiers existants legacy)
    assiya_dir = BASE / 'assiya'
    if assiya_dir.exists():
        files = sorted(
            f.name for f in assiya_dir.iterdir()
            if f.suffix.lower() in ALLOWED_EXT
        )
        if files:
            data['assiya']['cours'].setdefault('exercices', [])
            data['assiya']['cours']['exercices'] = files + [
                f for f in data['assiya']['cours'].get('exercices', [])
                if f not in files
            ]
    return data


@app.route('/')
def serve_index():
    return send_from_directory(str(BASE), 'index.html')


@app.route('/api/files')
def api_files():
    return jsonify(scan())


@app.route('/api/upload', methods=['POST'])
def api_upload():
    student = request.form.get('student', '').strip()
    type_   = request.form.get('type',    '').strip()
    subject = request.form.get('subject', '').strip()
    file    = request.files.get('file')

    if not all([student, type_, subject, file]):
        return jsonify({'error': 'Champs manquants'}), 400
    if student not in STUDENTS:
        return jsonify({'error': 'Élève inconnu'}), 400
    if type_ not in ('cours', 'controles'):
        return jsonify({'error': 'Type invalide'}), 400
    if not re.match(r'^[\w\-]+$', subject):
        return jsonify({'error': 'Nom de matière invalide (lettres, chiffres, tirets)'}), 400
    if Path(file.filename).suffix.lower() not in ALLOWED_EXT:
        return jsonify({'error': 'Seuls les fichiers .html et .pdf sont acceptés'}), 400

    dest_dir = BASE / STUDENTS[student]['folder'] / type_ / subject
    dest_dir.mkdir(parents=True, exist_ok=True)

    safe = re.sub(r'[^\w\-\.]', '-', file.filename).lower().strip('-')
    if not safe:
        return jsonify({'error': 'Nom de fichier invalide'}), 400

    dest = dest_dir / safe
    file.save(str(dest))
    rel = str(dest.relative_to(BASE))

    try:
        subprocess.run(['git', 'add', rel], cwd=str(BASE), check=True, capture_output=True)
        msg = f"Ajouter : {safe} ({STUDENTS[student]['name']} / {type_} / {subject})"
        subprocess.run(['git', 'commit', '-m', msg], cwd=str(BASE), check=True, capture_output=True)
    except subprocess.CalledProcessError:
        pass  # Upload réussi même si git n'est pas dispo

    return jsonify({'success': True, 'path': rel, 'filename': safe})


@app.route('/<path:p>')
def serve_static(p):
    return send_from_directory(str(BASE), p)


if __name__ == '__main__':
    print('\n🚀  Serveur lancé → http://localhost:5000\n')
    app.run(port=5000)
