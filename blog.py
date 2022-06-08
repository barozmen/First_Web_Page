from flask import Flask,render_template,flash,redirect,url_for,logging,request,session
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
import email
from functools import wraps # Kullanıcı girişi için kullanılan ve kullanıcı girişi yapılmadığında yönlendirme yapmak için kullanılır.(Flask Decorator)



def login_required(f):  #Kullanıcı Giriş Decorator
    @wraps(f) # Decorator ile kullanıcı girişi yapılmadığında yönlendirme yapmak için kullanılır.
    def decorated_function(*args, **kwargs): 
        if "logged_in" in session: #Kullanıcı girişi yapıldıysa True dönecek.
            return f(*args, **kwargs) #Fonksiyonu çalıştır.
        else:
            flash("Bu sayfayı görüntülemek için giriş yapınız.","danger") #Kullanıcı girişi yapılmadıysa flash mesajı verecek.
            return redirect(url_for("login")) #Kullanıcı girişi yapılmadıysa login sayfasına yönlendirilecek.
        return f(*args, **kwargs) #Kullanıcı girişi yapıldıysa f() fonksiyonunu çalıştırır.
    return decorated_function #Kullanıcı girişi yapılmadıysa login_required() fonksiyonunu çalıştırır.

class RegisterForm(Form): #Kayıt olma formu oluşturma
    name = StringField("İsim Soyisim",validators=[DataRequired(),validators.Length(min=4,max=25)])
    user_name = StringField("Kullanıcı Adı",validators=[DataRequired(),validators.Length(min=5,max=25)])
    email = StringField("Email",validators = [DataRequired(),validators.Email(message="Lütfen geçerli bir email adresi giriniz !")])
    password =PasswordField("Parola : ",validators=[
        DataRequired(message="Lütfen bir parola belirleyin !"),
        validators.EqualTo(fieldname="confirm",message="Parolanız uyuşmuyor !")
    ])
    confirm = PasswordField("Parola Doğrula")

class LoginForm(Form):  #Kullanıcı girişi formu oluşturma
    user_name = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

#Makale Formu
class ArticleForm(Form): #Form classını kullanarak formu oluşturuyoruz.
    title = StringField("Makale Başlığı",validators=[validators.Length(min=5,max=100)]) #Makale başlığının uzunluğu kontrolü
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min=10)]) #Makale içeriğinin uzunluğu kontrolü


app = Flask(__name__) 
app.secret_key = "baroblog" #Flash Message'ları kullanabilmek için programa bir secret key vermek gerekiyor !

#Flask ile MySQL arasındaki bağlantılar
app.config["MYSQL_HOST"] = "localhost" 
app.config["MYSQL_USER"] = "root" 
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "baroblog" 
app.config["MYSQL_CURSORCLASS"] = "DictCursor"     


# MySql Konfigürasyonu sonrası obje oluşturma işlemi.
mysql = MySQL(app) 

#Ana Sayfa
@app.route("/") 
def index(): 
    return render_template("index.html")

#Hakkında sayfası
@app.route("/about")
def about():
    return render_template("about.html")

#Makale Sayfası ve sayfa numaralarına göre link açma
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor() #Veritabanından veri çekmek için cursor oluşturma.
    sorgu = "Select * from articles where id = %s" #Veritabanındaki id ile gelen id ile eşleşen verileri getir.
    result = cursor.execute(sorgu,(id,)) #Sorgu çalıştırma.
    if result > 0: #Eğer veri varsa
        article = cursor.fetchone() #Sorgu sonucu olan veriyi fetchone() fonksiyonu ile al.
        return render_template("article.html",article=article) #article.html sayfasını render et.
    else:
        return render_template("article.html")
    return "Article Id:" + id


#Kayıt olma sayfası
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate(): # form.validate() metodu eğer kayıt bilgilerinde bir sorun yok ise fonksiyona devam ettirir.
        name = form.name.data
        email = form.email.data
        user_name = form.user_name.data
        password = sha256_crypt.encrypt(form.password.data) #Parolayı sha256 ile şifreliyoruz.
    
        #Veritabanına aktarma işlemi
        cursor = mysql.connection.cursor() #mysql veritabanında işlem yapmak için gerekli cursor'ı bağlıyoruz.
        sorgu = "Insert into users(name,email,user_name,password) VALUES(%s,%s,%s,%s)"  # Girilen bilgileri veritabanına aktarma işlemi
        cursor.execute(sorgu,(name,email,user_name,password)) #cursor ile sorgu arasındaki bağlantı.
        mysql.connection.commit() # Veritabanında silme ve güncelleme işlemi için commit yapmak şart!
        cursor.close() #İşlem sonrası veritabanı kapatma.
        flash("Kayıt işlemi başarılı !","success") #Flash mesajını cursor.close() işleminden hemen sonra bildirim olarak patlatıyoruz.

        return redirect(url_for("login")) #Kullanıcı bilgierini girip kayıt ol dedikten sonra post request gereği 'redirect' yardımı ile login'e gideriz.
    else:
        return render_template("register.html",title= "register",form=form)  

#Kullanıcı Giriş sayfası
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST": 
        user_name = form.user_name.data
        password_entered = form.password.data #Form'daki bilgiler alındı. Sonraki aşamada mysql veritabanından kontrol edeceğiz.
        cursor = mysql.connection.cursor () #Veritabanı üzerinde işlem yapmak için cursor bağlantısı yapılır.
        sorgu = "Select * From users where user_name = %s" #Veritabanından gelecek işlemi yönlendiriyoruz.
        result = cursor.execute(sorgu,(user_name,)) #username sonundaki ',' demet olarak algılanması için. Dönecek değer kontrolü yapılır 
        if result > 0:
            data = cursor.fetchone() #Kullanıcının tüm bilgileri mysql'den çekilir.
            real_password = data["password"] #Gerçek parola sorgusu için veritabanındaki password datası sözlük olarak çekildi.
            if sha256_crypt.verify(password_entered,real_password):
                flash("Giriş başarılı !","success")
                session["logged_in"] = True #Giriş yapıldıktan sonra session'a bilgileri atıyoruz.
                session["user_name"] = user_name #Kullanıcı adını session'a atıyoruz.

                return redirect(url_for("index")) #Giriş yapıldıktan sonra index sayfasına yönlendiriyoruz.
            else:
                flash("Parola yanlış !","danger") #Parola yanlış ise flash mesajını veriyoruz.
                return redirect(url_for("login")) #Giriş olmadığı için tekrar Login'e gönderir.

        else: 
            flash("Kullanıcı bulunamamaktadır !","danger") #Danger kodlu hata mesajı patlatma
            return redirect(url_for("login")) #Tekrar login' dizinine dönderir.

    return render_template("/login.html",form=form)  

#Logout işlemi
@app.route("/logout")
def logout():
    session.clear() #Session'ı temizliyoruz.
    return redirect(url_for("index")) #index sayfasına yönlendiriyoruz.

@app.route("/dashboard")
@login_required #Bu fonksiyonu çağırmak için login olması gerekiyor.
def dashboard():
    cursor = mysql.connection.cursor() #Veritabanından veri çekmek için cursor bağlantısı yapılır.
    sorgu = "Select * From articles where author = %s" #Veritabanındaki kullanıcı bilgileri çekmek için sorgu yazılır.
    result = cursor.execute(sorgu,(session["user_name"],)) #Sorgu çalıştırılır.
    if result > 0: #Eğer sorgu sonucunda veri varsa
        articles = cursor.fetchall() #Tüm verileri çekmek için fetchall() kullanılır.
        return render_template("dashboard.html",articles=articles) #dashboard.html sayfasına gönderilir.
    else:
        return render_template("dashboard.html")
    
#Makale Sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor() #Veritabanından veri çekmek için cursor bağlantısı yapılır.
    sorgu = "Select * From articles" #Veritabanındaki tüm makaleleri çekmek için sorgu.
    result = cursor.execute(sorgu) #Sorgu çalıştırılır.
    if result > 0: #Eğer sorgu sonucunda veri varsa
        articles = cursor.fetchall() #Tüm makaleleri çekmek için fetchall() fonksiyonu kullanılır.
        return render_template("articles.html",articles=articles) #Articles.html sayfasına yönlendiriyoruz.
    else:
        return render_template("articles.html")
    

#Makale Ekleme
@app.route("/addarticle",methods = ["GET","POST"]) 
def addarticle():
    form = ArticleForm(request.form) #Form oluşturulur.
    if request.method == "POST" and form.validate(): #Form doğru girildiyse
        title = form.title.data #Form'daki bilgiler alınır.
        content = form.content.data #Form'daki bilgiler alınır.

        cursor = mysql.connection.cursor() #Veritabanı üzerinde işlem yapmak için cursor bağlantısı yapılır.
        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)" #Veritabanına ekleme işlemi
        cursor.execute(sorgu,(title,session["user_name"],content)) #cursor ile sorgu arasındaki bağlantı.
        mysql.connection.commit() #Veritabanında silme ve güncelleme işlemi için commit yapmak şart!
        cursor.close() #İşlem sonrası veritabanı kapatma.
        flash("Makale başarıyla eklendi !","success") #Flash mesajını cursor.close() işleminden hemen sonra bildirim olarak patlatıyoruz.
        
        return redirect(url_for("dashboard")) #Makale eklendiğinde dashboard sayfasına yönlendiriyoruz.        
    return render_template("addarticle.html",form=form) #Formu gönderiyoruz.

#Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author = %s and id = %s"
    result = cursor.execute(sorgu,(session["user_name"],id))
    if result > 0:
        sorgu2 = "Delete from articles where id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok !","danger")
        return redirect(url_for("index"))

#Makale Güncelleme
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * From articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["user_name"]))
        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok !","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form=form)
    else:
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "Update articles Set title = %s, content = %s where id = %s"

        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi !","success")
        return redirect(url_for("dashboard"))   

#Search URL
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET": 
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword") #Formdan gelen keyword değeri alınır.
        cursor = mysql.connection.cursor() #Veritabanından veri çekmek için cursor bağlantısı yapılır.
        sorgu = "Select * from articles where title like'%" + keyword + "%'" #Veritabanındaki keyword ile başlayan makaleleri çekmek için sorgu.
        result = cursor.execute(sorgu) #Sorgu çalıştırılır.
        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı !","warning") #Eğer sorgu sonucunda veri yoksa
            return redirect(url_for("articles")) #Articles.html sayfasına yönlendiriyoruz.
        else:
            articles = cursor.fetchall() #Tüm makaleleri çekmek için fetchall() fonksiyonu kullanılır.
            return render_template("articles.html",articles=articles) #Articles.html sayfasına yönlendiriyoruz.




if __name__ == "__main__": #Eğer __name__ değişkeni __main__ ise açılış işlemi yapılır.
    app.run(debug=True) #Debug modu açılır.


    
    
