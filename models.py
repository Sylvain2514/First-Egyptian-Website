import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# import numpy as np is a convention
import numpy as np
# we need matplotlib just to read and show data
from matplotlib import pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageFont, ImageDraw
# from operator import itemgetter, attrgetter, methodcaller
import functools

UPLOAD_FOLDER = "static/picture"

db = SQLAlchemy()


class Picture(db.Model):
    __tablename__ = "pictures"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String)
    time_period = db.Column(db.String)
    place_picture_taken = db.Column(db.String)
    place_origin_hieroglyphs = db.Column(db.String)
    img_link = db.Column(db.String, nullable=False)
    preprocesses = db.relationship("Preprocess", backref="picture", lazy=True)

    def add_preprocess(self, process_name):
        p = Preprocess(process_name=process_name, picture_id=self.id)
        db.session.add(p)
        db.session.commit()


class Preprocess(db.Model):
    __tablename__ = "preprocesses"
    id = db.Column(db.Integer, primary_key=True)
    picture_id = db.Column(db.Integer,
                           db.ForeignKey("pictures.id"),
                           nullable=False)
    process_name = db.Column(db.String, nullable=False)
    img_link = db.Column(db.String)
    is_hiero_processed = db.Column(db.Boolean, nullable=False, default=False)
    hieros = db.relationship("Hiero", backref="preprocess", lazy=True)

    def __init__(self):
        self.preprocess_img = None
        self.preprocess_np = None
        self.preprocess_background = 0
        self.picture_matrix = []
        self.localized_hieros = []
        self.nb_of_col = 0
        self.nb_of_row = 0

    def preprocess_image(self):
        """Will preprocess picture and store it
         in self.preprocess image and np """

        filename = self.picture.img_link
        path_to_picture = os.path.join(UPLOAD_FOLDER, filename)
        self.preprocess_img = Image.open(path_to_picture)

        """ For the moment, only black and white preprocess
            'L' mode grayscale no alpha (transparency) """
        if self.process_name == "blackwhite":
            self.preprocess_img = self.preprocess_img.convert('L')
        else:
            self.preprocess_img = self.preprocess_img.convert('L')

        self.preprocess_np = np.array(self.preprocess_img)
        self.nb_of_row = self.preprocess_np.shape[0]
        self.nb_of_col = self.preprocess_np.shape[1]
        self.determine_preprocess_background()

    def create_surround_hiero(self):
        for hiero in self.localized_hieros:
            hiero.surround_hiero(self.preprocess_img)

        self.img_link = "pp_" + str(self.id) + "_surround.png"
        self.preprocess_img.save(os.path.join(UPLOAD_FOLDER,
                                              self.img_link), "PNG")

    def determine_preprocess_background(self):
        """ the background value depends on the pre-process, not the image """
        if self.preprocess_np is None:
            self.preprocess_image()
        self.preprocess_background = self.preprocess_np[0, 0]

    def build_picture_matrix(self):
        self.picture_matrix = [[None for x in range(self.nb_of_col)]
                               for y in range(self.nb_of_row)]

        for row in range(self.nb_of_row):
            for col in range(self.nb_of_col):
                plot_value = self.preprocess_np[row, col]
                plot = Plot(int(plot_value))
                plot.x = col
                plot.y = row
                plot.check_if_plot_hiero(self.preprocess_background)
                self.picture_matrix[row][col] = plot

    def localize_hieros(self):
        """ Will populate self.localized_hieros with all Hiero Objects
            found on the preprocessed picture."""

        self.preprocess_image()
        self.determine_preprocess_background()
        self.build_picture_matrix()

        self.localized_hieros = []

        for row in range(self.nb_of_row):
            for col in range(self.nb_of_col):
                plot = self.picture_matrix[row][col]
                if plot.is_plot_hiero and not plot.is_checked:
                    plot.is_checked = True
                    localized_plots = self.define_new_hiero_plots(plot)
                    new_hiero = Hiero()
                    new_hiero.preprocess_id = self.id
                    new_hiero.localized_plots = localized_plots
                    new_hiero.calculate_min_max()
                    if new_hiero.is_a_real_hiero():
                        self.localized_hieros.append(new_hiero)

    def define_new_hiero_plots(self, starting_plot):
        localized_plots = []
        localized_plots.append(starting_plot)

        index = 0
        while index < len(localized_plots):
            localized_plots = self.lookForNextPlot(localized_plots, index)
            index += 1

        return localized_plots

    def lookForNextPlot(self, localized_plots, index):
        current_plot = localized_plots[index]
        x = current_plot.x
        y = current_plot.y
        for i in [-2, -1, 0, 1, 2]:
            for j in [-2, -1, 0, 1, 2]:
                ok1 = (x+i > 0) and (y+j > 0)
                ok2 = (x+i < self.nb_of_col) and (y+j < self.nb_of_row)
                is_next_plot_inside_picture = ok1 and ok2

                if is_next_plot_inside_picture:
                    next_plot = self.picture_matrix[y+j][x+i]
                    if next_plot.is_plot_hiero and not next_plot.is_checked:
                        self.picture_matrix[y+j][x+i].is_checked = True
                        localized_plots.append(next_plot)
        return localized_plots


class Hiero(db.Model):
    __tablename__ = "hieros"
    id = db.Column(db.Integer, primary_key=True)
    preprocess_id = db.Column(db.Integer,
                              db.ForeignKey("preprocesses.id"),
                              nullable=False)
    order = db.Column(db.Integer, nullable=False)
    min_x = db.Column(db.Integer, nullable=False)
    max_x = db.Column(db.Integer, nullable=False)
    min_y = db.Column(db.Integer, nullable=False)
    max_y = db.Column(db.Integer, nullable=False)
    img_link = db.Column(db.String)
#    plots = db.relationship("Plot", backref="hiero", lazy=True)

    def __init__(self):
        self.localized_plots = []
        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0
        self.order = 0

    def is_a_real_hiero(self):
        if len(self.localized_plots) > 10:
            return True
        else:
            return False

    def calculate_min_max(self):
        self.min_x = self.localized_plots[0].x
        self.max_x = self.localized_plots[0].y
        self.min_y = self.localized_plots[0].x
        self.max_y = self.localized_plots[0].y

        for plot in self.localized_plots:
            if plot.x > self.max_x:
                self.max_x = plot.x
            elif plot.x < self.min_x:
                self.min_x = plot.x
            if plot.y > self.max_y:
                self.max_y = plot.y
            elif plot.y < self.min_y:
                self.min_y = plot.y

    def create_hiero_pic(self, preprocess_np, background=None):
        if background is None:
            background = preprocess_np[0, 0]
        self.calculate_min_max()

        """ PIL.Image.new(mode, size, color=0)
        size – A 2-tuple, containing (width, height) in pixels. """
        hiero_im = Image.new('L', (self.max_x - self.min_x + 6,
                                   self.max_y - self.min_y + 6),
                             int(background))
        hiero_dr = ImageDraw.Draw(hiero_im)
        for plot in self.localized_plots:
            new_x = plot.x - self.min_x + 3
            new_y = plot.y - self.min_y + 3
            new_value = int(plot.value)
            hiero_dr.point((new_x, new_y), new_value)


        self.img_link = 'pp_' + str(self.preprocess_id) + '_hiero_' + \
                        str(self.id) + ".png"

        hiero_im.save(os.path.join(UPLOAD_FOLDER,
                                   "hieros",
                                   self.img_link), "PNG")

    def surround_hiero(self, preprocess_img):
        new_min_x = self.min_x - 3
        new_max_x = self.max_x + 3
        new_min_y = self.min_y - 3
        new_max_y = self.max_y + 3

        dr = ImageDraw.Draw(preprocess_img)
        dr.line(((new_min_x, new_min_y),
                 (new_max_x, new_min_y)), fill="red", width=2)
        dr.line(((new_max_x, new_min_y),
                 (new_max_x, new_max_y)), fill="red", width=2)
        dr.line(((new_max_x, new_max_y),
                 (new_min_x, new_max_y)), fill="red", width=2)
        dr.line(((new_min_x, new_max_y),
                 (new_min_x, new_min_y)), fill="red", width=2)


class Plot():
    """ hiero_id, x, y, value """
    def __init__(self, value=0):
        self.value = value
        self.is_plot_hiero = False
        self.is_checked = False

    def check_if_plot_hiero(self, preprocess_background, power=40):
        ok1 = (int(self.value) - int(preprocess_background)) > power
        ok2 = (int(preprocess_background) - int(self.value)) > power
        if ok1 or ok2:
            self.is_plot_hiero = True
        else:
            self.is_plot_hiero = False
        return self.is_plot_hiero
