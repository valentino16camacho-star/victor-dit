import eventlet
eventlet.monkey_patch()

import os, time, random, smtplib, json, mimetypes
from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_socketio import SocketIO, emit

mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/webm', '.webm')
mimetypes.add_type('video/quicktime', '.mov')

app = Flask(__name__)
app.secret_key = 'victor_sullana_omega_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- CONFIGURACIÓN DE GMAIL ---
MI_CORREO = "vakecama32@gmail.com" 
MI_PASSWORD = "kehn ludf ogeo mxmh" 

UPLOADS = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOADS
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 
if not os.path.exists(UPLOADS): os.makedirs(UPLOADS)

DB_PATH = 'datos_red_social.json'

def cargar_datos():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "usuarios" not in data: data["usuarios"] = {}
                if "foros" not in data: data["foros"] = {"General": []}
                if "chats" not in data: data["chats"] = {}
                return data
        except:
            return {"usuarios": {}, "foros": {"General": []}, "chats": {}}
    return {"usuarios": {}, "foros": {"General": []}, "chats": {}}

def guardar_datos():
    data = {
        "usuarios": usuarios_db,
        "foros": foro_data,
        "chats": chats_privados
    }
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

datos_iniciales = cargar_datos()
usuarios_db = datos_iniciales["usuarios"]
foro_data = datos_iniciales["foros"]
chats_privados = datos_iniciales["chats"]
pendientes = {}

def enviar_codigo(correo_destino, codigo):
    msg = MIMEMultipart()
    msg['From'] = MI_CORREO
    msg['To'] = correo_destino
    msg['Subject'] = f"🤖 CÓDIGO ANTI-ROBOT: {codigo}"
    msg.attach(MIMEText(f"Tu código de acceso es: {codigo}", 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        server.login(MI_CORREO, MI_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"❌ ERROR GMAIL: {e}")
        return False

@app.route('/')
def index():
    if 'user' in session: return redirect('/foro/General')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        u = (request.form.get('u') or "").strip()
        e = (request.form.get('e') or "").strip()
        p = (request.form.get('p') or "").strip()
        if not u or not e or not p:
            flash("❌ Completa todos los campos.")
            return redirect(url_for('registro'))
        if u in usuarios_db:
            flash("❌ Usuario ya registrado.")
            return redirect(url_for('registro'))
        
        cod = str(random.randint(100000, 999999))
        pendientes[u] = {"p": p, "e": e, "cod": cod}
        enviar_codigo(e, cod)
        return redirect(url_for('verificar', usuario=u))
    return render_template('registro.html')

@app.route('/verificar/<usuario>', methods=['GET', 'POST'])
def verificar(usuario):
    if request.method == 'POST':
        c = (request.form.get('c') or "").strip()
        datos = pendientes.get(usuario)
        if datos and datos['cod'] == c:
            usuarios_db[usuario] = {
                "p": datos['p'], "e": datos['e'],
                "bio": "¡Hola! Soy nuevo.",
                "fecha_union": datetime.now().strftime("%d/%m/%Y"),
                "avatar": None, "amigos": [], "solicitudes": [],
                "estado": "Activo"
            }
            guardar_datos()
            session['user'] = usuario
            return redirect('/foro/General')
    return render_template('verificar.html', usuario=usuario)

@app.route('/login', methods=['POST'])
def login():
    u = request.form.get('u', '').strip()
    p = request.form.get('p', '').strip()
    if u in usuarios_db and usuarios_db[u].get('p') == p:
        session['user'] = u
        return redirect('/foro/General')
    flash("❌ Datos incorrectos.")
    return redirect('/')

@app.route('/foro/<categoria>')
def ver_foro(categoria):
    if 'user' not in session: return redirect('/')
    if categoria not in foro_data: foro_data[categoria] = []
    return render_template('admin.html', posts=foro_data[categoria], cat=categoria, categorias=list(foro_data.keys()), mi_usuario=session['user'])

@app.route('/publicar/<categoria>', methods=['POST'])
def publicar(categoria):
    if 'user' not in session: return redirect('/')
    texto = request.form.get('mensaje', '').strip()
    archivo = request.files.get('archivo')
    fname = None
    ftype = None
    
    if archivo and archivo.filename != '':
        fname = secure_filename(archivo.filename)
        ext = os.path.splitext(fname)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.gif']: ftype = 'img'
        elif ext in ['.mp4', '.webm', '.mov']: ftype = 'vid'
        archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    
    post = {
        "id": int(time.time()),
        "autor": session['user'],
        "contenido": texto,
        "archivo": fname,
        "tipo": ftype,
        "comentarios": [],
        "fecha": datetime.now().strftime("%H:%M")
    }
    
    if categoria not in foro_data: foro_data[categoria] = []
    foro_data[categoria].insert(0, post)
    socketio.emit('nueva_publicacion', {'categoria': categoria, 'post': post})
    guardar_datos()
    return redirect(url_for('ver_foro', categoria=categoria))

@app.route('/comentar/<categoria>/<int:post_id>', methods=['POST'])
def comentar(categoria, post_id):
    if 'user' not in session: return redirect('/')
    texto = request.form.get('comentario', '').strip()
    if texto:
        for p in foro_data.get(categoria, []):
            if p['id'] == post_id:
                nuevo_com = {"autor": session['user'], "texto": texto, "fecha": datetime.now().strftime("%H:%M")}
                p['comentarios'].append(nuevo_com)
                socketio.emit('nuevo_comentario', {'post_id': post_id, 'categoria': categoria, 'comentario': nuevo_com})
        guardar_datos()
    return redirect(url_for('ver_foro', categoria=categoria))

@app.route('/perfil/<username>')
def ver_perfil(username):
    if 'user' not in session: return redirect('/')
    info = usuarios_db.get(username)
    if not info: return redirect('/')
    return render_template('perfil.html', perfil_user=username, info=info, mi_usuario=session['user'], categorias=list(foro_data.keys()))

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/salir')
def salir():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    socketio.run(app, debug=True)
