import os

from flask import Flask, render_template, jsonify, request
from werkzeug import secure_filename
from models import *

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
UPLOAD_FOLDER = "static/picture"
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

db.init_app(app)


def allowed_file(filename):
    ok1 = '.' in filename
    ok2 = filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    return ok1 and ok2


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/pictures")
def pictures():
    """List all pictures."""
    pictures = Picture.query.all()
    return render_template("pictures.html",
                           pictures=pictures)


@app.route("/pictures/<int:picture_id>")
def picture(picture_id):
    """List details about a single picture."""
    # Make sure picture exists.
    picture = Picture.query.get(picture_id)
    if picture is None:
        return render_template("error.html", message="No such picture.")

    # Get all preprocesses.
    preprocesses = picture.preprocesses
    return render_template("picture.html",
                           picture=picture,
                           preprocesses=preprocesses)


@app.route("/listhieros/<int:preprocess_id>")
def listhieros(preprocess_id):
    """List all hieros of a Pre-Process."""
    preprocess = Preprocess.query.get(preprocess_id)
    if preprocess is None:
        return render_template("error.html", message="No such preprocess.")

    hieros = preprocess.hieros

#    if not preprocess.is_hiero_processed:
#    for hiero in hieros:
#        hiero.create_hiero_pic(preprocess.preprocess_np,
#                               preprocess.preprocess_background)

    return render_template("listhieros.html",
                           preprocess=preprocess,
                           hieros=hieros)


@app.route("/addpicture", methods=["POST"])
def addpicture():
    """Add a picture."""

    # Get form information.
    description = request.form.get("description")
    time_period = request.form.get("time_period")
    preprocesses = request.form.getlist("preprocesses")

    f = request.files['picture_img']
    if f.filename == "":
        return render_template("error.html", message="No picture uploaded")
    if f and allowed_file(f.filename):
        filename = secure_filename(f.filename)
        f.save(os.path.join(UPLOAD_FOLDER, filename))

    p = Picture(description=description,
                time_period=time_period,
                img_link=filename)
    db.session.add(p)
    db.session.commit()

    new_filename = 'pict_' + str(p.id) + '.' + filename.rsplit('.', 1)[1].lower()
    os.rename(os.path.join(UPLOAD_FOLDER, filename),
              os.path.join(UPLOAD_FOLDER, new_filename))
    p.img_link = new_filename
    db.session.commit()

    for process_name in preprocesses:
        preprocess = Preprocess()
        preprocess.picture_id = p.id
        preprocess.process_name = process_name
        db.session.add(preprocess)
        db.session.commit()
        preprocess.localize_hieros()
        for hiero in preprocess.localized_hieros:
            db.session.add(hiero)
            db.session.commit()
            hiero.create_hiero_pic(preprocess.preprocess_np,
                                   preprocess.preprocess_background)
        preprocess.is_hiero_processed = True
        preprocess.create_surround_hiero()

        db.session.commit()

    return render_template("success.html", message="File has been uploaded")


def main():
    db.create_all()


if __name__ == "__main__":
    with app.app_context():
        main()
