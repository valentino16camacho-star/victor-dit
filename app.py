import os, time, random, smtplib, json, mimetypes
from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# AGREGADO: Forzar que el navegador reconozca videos correctamente
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/webm', '.webm')
mimetypes.add_type('video/quicktime', '.mov')

app = Flask(__name__)
app.secret_key = 'victor_sullana_omega_2026'

# --- CONFIGURACIÓN DE GMAIL ---
MI_CORREO = "vakecama32@gmail.com" 
MI_PASSWORD = "kehn ludf ogeo mxmh" 

UPLOADS = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOADS
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 

# AJUSTE: Soporte para textos muy largos en formularios (evita errores de memoria)
app.config['MAX_FORM_MEMORY_SIZE'] = 15 * 1024 * 1024

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
        # CORRECCIÓN: Uso de SSL y puerto 465 para garantizar el envío en servidores
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=12)
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
            print(f"⚠️ MODO PRUEBA ACTIVADO - El código para {u} es: {cod}")
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
    
    if not info or not isinstance(info, dict):
        flash("❌ El usuario no existe o datos corruptos.")
        return redirect(url_for('ver_foro', categoria='General'))
    
    if "visible_altura" not in info: info["visible_altura"] = True
    if "visible_meta" not in info: info["visible_meta"] = True
    if "visible_hw" not in info: info["visible_hw"] = True
    if "amigos" not in info: info["amigos"] = []
    if "solicitudes" not in info: info["solicitudes"] = []
    
    sus_posts = []
    for categoria, posts in foro_data.items():
        if isinstance(posts, list):
            for p in posts:
                if isinstance(p, dict) and p.get('autor') == username:
                    p_copy = p.copy()
                    p_copy['cat_origen'] = categoria
                    sus_posts.append(p_copy)
    
    sus_posts.sort(key=lambda x: x.get('id', 0), reverse=True)
    return render_template('perfil.html', perfil_user=username, info=info, posts=sus_posts, mi_usuario=session['user'], categorias=list(foro_data.keys()), usuarios_db=usuarios_db)

@app.route('/editar_perfil', methods=['POST'])
def editar_perfil():
    if 'user' not in session: return redirect('/')
    usuario = session['user']
    
    nueva_bio = request.form.get('bio', '').strip()
    nueva_altura = request.form.get('altura', '').strip()
    nueva_meta = request.form.get('meta_fisica', '').strip()
    nuevo_hw = request.form.get('hardware', '').strip()
    nuevo_estado = request.form.get('estado', 'Activo').strip()
    
    usuarios_db[usuario]['visible_altura'] = (request.form.get('visible_altura') == 'on')
    usuarios_db[usuario]['visible_meta'] = (request.form.get('visible_meta') == 'on')
    usuarios_db[usuario]['visible_hw'] = (request.form.get('visible_hw') == 'on')
    
    archivo = request.files.get('foto_perfil')
    
    if usuario not in usuarios_db: usuarios_db[usuario] = {}
    
    if nueva_bio: usuarios_db[usuario]['bio'] = nueva_bio
    usuarios_db[usuario]['altura'] = nueva_altura
    usuarios_db[usuario]['meta_fisica'] = nueva_meta
    usuarios_db[usuario]['hardware'] = nuevo_hw
    usuarios_db[usuario]['estado'] = nuevo_estado

    if archivo and archivo.filename != '':
        ext = os.path.splitext(archivo.filename)[1]
        filename = secure_filename(f"avatar_{usuario}_{int(time.time())}{ext}")
        archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        usuarios_db[usuario]['avatar'] = filename
        
    guardar_datos()
    return redirect(url_for('ver_perfil', username=usuario))

@app.route('/enviar_solicitud/<target>')
def enviar_solicitud(target):
    if 'user' not in session: return redirect('/')
    me = session['user']
    if target in usuarios_db and target != me:
        if not isinstance(usuarios_db[target], dict): usuarios_db[target] = {}
        if "solicitudes" not in usuarios_db[target]: usuarios_db[target]["solicitudes"] = []
        if me not in usuarios_db[target]["solicitudes"]:
            usuarios_db[target]["solicitudes"].append(me)
            guardar_datos()
    return redirect(url_for('ver_perfil', username=target))

@app.route('/aceptar_solicitud/<remitente>')
def aceptar_solicitud(remitente):
    if 'user' not in session: return redirect('/')
    me = session['user']
    if remitente in usuarios_db[me].get("solicitudes", []):
        if "amigos" not in usuarios_db[me]: usuarios_db[me]["amigos"] = []
        if "amigos" not in usuarios_db[remitente]: usuarios_db[remitente]["amigos"] = []
        usuarios_db[me]["amigos"].append(remitente)
        usuarios_db[remitente]["amigos"].append(me)
        usuarios_db[me]["solicitudes"].remove(remitente)
        guardar_datos()
    return redirect(url_for('ver_perfil', username=me))

@app.route('/eliminar_amigo/<amigo>')
def eliminar_amigo(amigo):
    if 'user' not in session: return redirect('/')
    me = session['user']
    if amigo in usuarios_db[me].get("amigos", []):
        usuarios_db[me]["amigos"].remove(amigo)
        if me in usuarios_db[amigo].get("amigos", []): usuarios_db[amigo]["amigos"].remove(me)
        guardar_datos()
    return redirect(url_for('ver_perfil', username=amigo))

# --- RUTAS DE FORO ---

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
                p['comentarios'].append({
                    "autor": session['user'], "texto": comentario_txt, "fecha": datetime.now().strftime("%H:%M")
                })
        guardar_datos()
    return redirect(url_for('ver_foro', categoria=categoria))

@app.route('/eliminar/<categoria>/<int:post_id>')
def eliminar(categoria, post_id):
    if 'user' not in session: return redirect('/')
    if categoria in foro_data:
        foro_data[categoria] = [p for p in foro_data[categoria] if not (p['id'] == post_id and p['autor'] == session['user'])]
        guardar_datos()
    return redirect(url_for('ver_foro', categoria=categoria))

@app.route('/crear_categoria', methods=['POST'])
def crear_categoria():
    if 'user' not in session: return redirect('/')
    n = (request.form.get('nombre_cat') or "").strip()
    if n and n not in foro_data:
        foro_data[n] = []
        guardar_datos()
    return redirect(url_for('ver_foro', categoria=n if n else 'General'))

# --- SISTEMA DE CHATS PRIVADOS ---

@app.route('/mis_chats')
def mis_chats():
    if 'user' not in session: return redirect('/')
    me = session['user']
    mis_salas = []
    for sala_id in chats_privados:
        if me in sala_id.split('_'):
            partes = sala_id.split('_')
            otro = partes[1] if partes[0] == me else partes[0]
            mis_salas.append({"usuario": otro, "sala": sala_id})
    return render_template('lista_chats.html', salas=mis_salas, usuarios_db=usuarios_db, categorias=list(foro_data.keys()))

@app.route('/chat/<amigo>', methods=['GET', 'POST'])
def chat_privado(amigo):
    if 'user' not in session: return redirect('/')
    me = session['user']
    sala = "_".join(sorted([me, amigo]))
    
    if sala not in chats_privados: chats_privados[sala] = []

    for m in chats_privados[sala]:
        if m['envia'] == amigo:
            m['leido'] = True
    guardar_datos()

    if request.method == 'POST':
        msg = (request.form.get('mensaje') or "").strip()
        archivo = request.files.get('archivo')
        fname = None
        ftype = None

        if archivo and archivo.filename != '':
            fname = secure_filename(archivo.filename)
            ext = os.path.splitext(fname)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']: ftype = 'img'
            elif ext in ['.mp4', '.mov', '.avi', '.webm']: ftype = 'vid'
            else: ftype = 'file'
            archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))

        if msg or fname:
            chats_privados[sala].append({
                "envia": me, 
                "texto": msg, 
                "archivo": fname, 
                "tipo": ftype, 
                "fecha": datetime.now().strftime("%H:%M"),
                "leido": False 
            })
            guardar_datos()
        return redirect(url_for('chat_privado', amigo=amigo))

    return render_template('chat.html', amigo=amigo, mensajes=chats_privados[sala], mi_usuario=me, usuarios_db=usuarios_db, categorias=list(foro_data.keys()))

# --- API DE NOTIFICACIONES ---

@app.route('/api/contador_global')
def contador_global():
    if 'user' not in session:
        return jsonify({'total': 0})
    
    me = session['user']
    total = 0
    for sala_id, mensajes in chats_privados.items():
        if me in sala_id.split('_'):
            for m in mensajes:
                if m['envia'] != me and not m.get('leido', False):
                    total += 1
    return jsonify({'total': total})

@app.route('/api/mensajes/<amigo>')
def api_mensajes(amigo):
    if 'user' not in session: return ""
    me = session['user']
    sala = "_".join(sorted([me, amigo]))
    
    mensajes = chats_privados.get(sala, [])
    for m in mensajes:
        if m['envia'] == amigo:
            m['leido'] = True
    guardar_datos()
    
    return render_template('solo_mensajes.html', mensajes=mensajes, mi_usuario=me, usuarios_db=usuarios_db)

@app.route('/salir')
def salir():
    session.clear()
    return redirect('/')

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # CORRECCIÓN: Puerto dinámico para despliegue en la nube
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
