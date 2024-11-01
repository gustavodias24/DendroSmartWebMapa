import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from io import BytesIO

from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = 'PPKDOMALSENTANOPAU69'

client = MongoClient('mongodb://localhost:27017/')  
db = client['db']

db_credenciais = client["kaizenApp"]
col_credentials = db_credenciais["credenciais"]

fs = gridfs.GridFS(db)

KMZ_FOLDER = 'static/kmz_files'

# Página de login
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        token = request.form.get('token')
        if cred := col_credentials.find_one({'_id': token}):
            if cred.get('ativa'):
                session['token'] = token
                return redirect(url_for('kmz_list', id_do_usuario=token))
            else:
                return render_template('index.html', error='Esse token está desativado')
        else:
            return render_template('index.html', error='Token inválido')
    return render_template('index.html')

# Página com a lista de arquivos KMZ
@app.route('/kmz_list/<id_do_usuario>')
def kmz_list(id_do_usuario):
    files = db.fs.files.find({'id_do_usuario': id_do_usuario})
    files_list = []
    
    

    for file in files:
        files_list.append({
            'file_id': str(file['_id']),
            'filename': file['filename'],
            'contentType': file['contentType'],
            'uploadDate':  file['uploadDate'].strftime("%Y-%m-%d às %H:%M")
        })

    files_list.reverse()
    return render_template('kmz_list.html', kmz_files=files_list)

@app.route('/map_viewer/<file_id>')
def map_viewer(file_id):
    if 'token' not in session:
        return redirect(url_for('index'))
    
    # Renderiza a página HTML passando o file_id
    return render_template('map_viewer.html', file_id=file_id)

@app.route('/view_kmz/<file_id>')
def view_kmz(file_id):
    if 'token' not in session:
        return redirect(url_for('index'))

    try:
        file = fs.get(ObjectId(file_id))
        filename = file.filename

        # Cria um stream de bytes para o arquivo KMZ
        kmz_data = BytesIO(file.read())

        # Verifica se o arquivo é KMZ ou KML
        if filename.endswith('.kmz'):
            # Salva o KMZ em um arquivo temporário
            kmz_temp_path = f'/tmp/{filename}'
            with open(kmz_temp_path, 'wb') as kmz_temp_file:
                kmz_temp_file.write(kmz_data.getbuffer())

            # Converte KMZ para KML
            kml_temp_path = kmz_temp_path.replace('.kmz', '.kml')
            if not os.path.exists(kml_temp_path):
                subprocess.call(['ogr2ogr', '-f', 'KML', kml_temp_path, kmz_temp_path])

            # Retorna o caminho do KML gerado
            return send_file(kml_temp_path, mimetype='application/vnd.google-earth.kml+xml')
        
        elif filename.endswith('.kml'):
            # Serve diretamente o arquivo KML
            return send_file(BytesIO(kmz_data.getbuffer()), mimetype='application/vnd.google-earth.kml+xml')
        
        else:
            return "Arquivo não suportado.", 400

    except gridfs.errors.NoFile:
        return "Arquivo não encontrado.", 404
    if 'token' not in session:
        return redirect(url_for('index'))

    # Buscando o arquivo pelo file_id no GridFS
    try:
        file = fs.get(ObjectId(file_id))
        filename = file.filename

        # Cria um stream de bytes para o arquivo KMZ
        kmz_data = BytesIO(file.read())

        # Verifica se o arquivo é KMZ ou KML
        if filename.endswith('.kmz'):
            # Salva o KMZ em um arquivo temporário
            kmz_temp_path = f'/tmp/{filename}'
            with open(kmz_temp_path, 'wb') as kmz_temp_file:
                kmz_temp_file.write(kmz_data.getbuffer())

            # Converte KMZ para KML
            kml_temp_path = kmz_temp_path.replace('.kmz', '.kml')
            if not os.path.exists(kml_temp_path):
                subprocess.call(['ogr2ogr', '-f', 'KML', kml_temp_path, kmz_temp_path])

            # Serve o arquivo KML
            return send_file(kml_temp_path, mimetype='application/vnd.google-earth.kml+xml')
        elif filename.endswith('.kml'):
            # Serve diretamente o arquivo KML
            return send_file(BytesIO(kmz_data.getbuffer()), mimetype='application/vnd.google-earth.kml+xml')
        else:
            return "Arquivo não suportado.", 400  # Retorna um erro se não for KMZ ou KML

    except gridfs.errors.NoFile:
        return "Arquivo não encontrado.", 404


@app.route('/upload_kmz', methods=['POST'])
def upload_kmz():
    id_do_usuario = request.form.get('id_do_usuario')
    file = request.files['file']

    if not id_do_usuario or not file:
        return jsonify({'error': 'id_do_usuario e arquivo são necessários!'}), 400

    fuso_brasil = pytz.timezone("America/Sao_Paulo")
    data_hora_atual = datetime.now(fuso_brasil)
    data_hora_formatada = data_hora_atual.strftime("%d/%m/%Y às %H:%M")

    file_id = fs.put(file, filename=file.filename, contentType=file.content_type, id_do_usuario=id_do_usuario, data_hora_formatada=data_hora_formatada) 

    return jsonify({'message': 'Arquivo salvo com sucesso!', 'file_id': str(file_id)}), 201



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)
