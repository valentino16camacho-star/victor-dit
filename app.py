import eventlet
eventlet.monkey_patch() # Crucial para que Render no dé error de RLock

import os, time, random, smtplib, json, mimetypes
from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_socketio import SocketIO, emit # Importación limpia

# AGREGADO: Forzar que el navegador reconozca videos correctamente
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/webm', '.webm')
mimetypes.add_type('video/quicktime', '.mov')

app = Flask(__name__)
app.secret_key = 'victor_sullana_omega_2026'
# Configuración optimizada para Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet') 

# --- CONFIGURACIÓN DE GMAIL ---
MI_CORREO = "vakecama32@gmail.com" 
MI_PASSWORD = "kehn ludf ogeo mxmh" 

UPLOADS = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOADS
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 
if not os.path.exists(UPLOADS): os.makedirs(UPLOADS)

# --- SISTEMA DE PERSISTENCIA ---
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

# Inicialización global
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

# --- RUTAS DE ACCESO ---
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
        
        if enviar_codigo(e, cod):
            print(f"✅ Correo enviado a {e}")
        else:
            flash(f"🛠️ MODO PRUEBA: Gmail no configurado. Tu código es: {cod}")
        
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
                "bio": "¡Hola! Soy nuevo en Víctor-dit.",
                "fecha_union": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "avatar": None, "amigos": [], "solicitudes": [],
                "altura": "", "meta_fisica": "", "hardware": "", "estado": "Activo",
                "visible_altura": True, "visible_meta": True, "visible_hw": True
            }
            guardar_datos()
            session['user'] = usuario
            return redirect('/foro/General')
        flash("❌ Código incorrecto.")
    return render_template('verificar.html', usuario=usuario)

@app.route('/login', methods=['POST'])
def login():
    u = (request.form.get('u') or "").strip()
    p = (request.form.get('p') or "").strip()
    if u in usuarios_db and isinstance(usuarios_db[u], dict) and usuarios_db[u].get('p') == p:
        session['user'] = u
        return redirect('/foro/General')
    flash("❌ Datos incorrectos.")
    return redirect(url_for('index'))

# --- RUTAS DE PERFIL Y AMIGOS ---
@app.route('/buscar', methods=['GET', 'POST'])
def buscar():
    if 'user' not in session: return redirect('/')
    resultados = []
    query = request.form.get('query', '').strip()
    if query:
        for u in usuarios_db:
            if query.lower() in u.lower() and u != session['user']:
                info_u = usuarios_db[u] if isinstance(usuarios_db[u], dict) else {}
                resultados.append({"nombre": u, "avatar": info_u.get('avatar')})
    return render_template('buscar.html', resultados=resultados, query=query, mi_usuario=session['user'], categorias=list(foro_data.keys()))

@app.route('/perfil/<username>')
def ver_perfil(username):
    if 'user' not in session: return redirect('/')
    info = usuarios_db.get(username)
    if not info: return redirect('/foro/General')
    
    sus_posts = []
    for categoria, posts in foro_data.items():
        for p in posts:
            if p.get('autor') == username:
                p_copy = p.copy()
                p_copy['cat_origen'] = categoria
                sus_posts.append(p_copy)
    
    sus_posts.sort(key=lambda x: x.get('id', 0), reverse=True)
    return render_template('perfil.html', perfil_user=username, info=info, posts=sus_posts, mi_usuario=session['user'], categorias=list(foro_data.keys()), usuarios_db=usuarios_db)

@app.route('/editar_perfil', methods=['POST'])
def editar_perfil():
    if 'user' not in session: return redirect('/')
    usuario = session['user']
    usuarios_db[usuario]['bio'] = request.form.get('bio', '').strip()
    usuarios_db[usuario]['altura'] = request.form.get('altura', '').strip()
    usuarios_db[usuario]['meta_fisica'] = request.form.get('meta_fisica', '').strip()
    usuarios_db[usuario]['hardware'] = request.form.get('hardware', '').strip()
    usuarios_db[usuario]['estado'] = request.form.get('estado', 'Activo').strip()
    
    archivo = request.files.get('foto_perfil')
    if archivo and archivo.filename != '':
        filename = secure_filename(f"avatar_{usuario}_{int(time.time())}{os.path.splitext(archivo.filename)[1]}")
        archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        usuarios_db[usuario]['avatar'] = filename
        
    guardar_datos()
    return redirect(url_for('ver_perfil', username=usuario))

# --- RUTAS DE FORO (CORREGIDAS) ---
@app.route('/foro/<categoria>')
def ver_foro(categoria):
    if 'user' not in session: return redirect('/')
    if categoria not in foro_data: foro_data[categoria] = []
    return render_template('admin.html', posts=foro_data[categoria], cat=categoria, categorias=list(foro_data.keys()), mi_usuario=session['user'])

@app.route('/publicar/<categoria>', methods=['POST'])
def publicar(categoria):
    if 'user' not in session: return redirect('/')
    texto = (request.form.get('mensaje') or "").strip()
    archivo = request.files.get('archivo')
    fname = None
    ftype = None
    if archivo and archivo.filename != '':
        fname = secure_filename(archivo.filename)
        ext = os.path.splitext(fname)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']: ftype = 'img'
        elif ext in ['.mp4', '.mov', '.avi', '.webm']: ftype = 'vid' 
        archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    
    post = {
        "id": int(time.time()), "autor": session['user'], "contenido": texto,
        "archivo": fname, "tipo": ftype, "comentarios": [], "fecha": datetime.now().strftime("%H:%M")
    }
    if categoria not in foro_data: foro_data[categoria] = []
    foro_data[categoria].insert(0, post)
    
    # CORRECCIÓN: Se quitó broadcast=True para evitar el Error 500
    socketio.emit('nueva_publicacion', {'categoria': categoria, 'post': post})
    
    guardar_datos() 
    return redirect(url_for('ver_foro', categoria=categoria))

@app.route('/comentar/<categoria>/<int:post_id>', methods=['POST'])
def comentar(categoria, post_id):
    if 'user' not in session: return redirect('/')
    comentario_txt = (request.form.get('comentario') or "").strip()
    if comentario_txt:
        for p in foro_data.get(categoria, []):
            if p['id'] == post_id:
                if "comentarios" not in p: p["comentarios"] = []
                nuevo_com = {
                    "autor": session['user'], "texto": comentario_txt, "fecha": datetime.now().strftime("%H:%M")
                }
                p['comentarios'].append(nuevo_com)
                
                # CORRECCIÓN: Se quitó broadcast=True para evitar el Error 500
                socketio.emit('nuevo_comentario', {
                    'post_id': post_id, 
                    'categoria': categoria, 
                    'comentario': nuevo_com
                })
        guardar_datos()
    return redirect(url_for('ver_foro', categoria=categoria))

# --- EL RESTO DE TUS RUTAS (CHATS, WEBRTC, CONTADORES) SIGUEN IGUAL ---
@app.route('/chat/<amigo>', methods=['GET', 'POST'])
def chat_privado(amigo):
    if 'user' not in session: return redirect('/')
    me = session['user']
    sala = "_".join(sorted([me, amigo]))
    if sala not in chats_privados: chats_privados[sala] = []

    if request.method == 'POST':
        msg = (request.form.get('mensaje') or "").strip()
        nuevo_msg = {"envia": me, "texto": msg, "fecha": datetime.now().strftime("%H:%M"), "leido": False}
        chats_privados[sala].append(nuevo_msg)
        socketio.emit('mensaje_chat', {'sala': sala, 'msg': nuevo_msg})
        guardar_datos()
        return redirect(url_for('chat_privado', amigo=amigo))
    return render_template('chat.html', amigo=amigo, mensajes=chats_privados[sala], mi_usuario=me, usuarios_db=usuarios_db, categorias=list(foro_data.keys()))

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
