import datetime
import json
from math import sin, pi
from pyglet.gl import *
from pyglet.window import key
from pyglet.window import mouse


SCALE = 3


def lltoxy(long, lat):
    return ((long - MIN_LONG) * 2, (lat - MIN_LAT) * 2)


def gen_vertices(long, lat):
    xout = 1.5
    x, y = lltoxy(long, lat)
    return [x - (xout*SCALE), y - SCALE, x, y + (1.8*SCALE), x + (xout*SCALE), y - SCALE]


def gen_color(mag, alpha):
    yellow = 1 - ((mag-MIN_MAG) / (MAX_MAG-MIN_MAG))
    return [1, yellow, 0, alpha, 1, yellow, 0, alpha, 1, yellow, 0, alpha]


# We do 'raise BadQuake' when there's ungraphable data in the file.
class BadQuake:
    pass


class Quake:
    def __init__(self, data):
        self.title = data['properties']['title']
        self.longitude = data['geometry']['coordinates'][0]
        self.latitude = data['geometry']['coordinates'][1]
        self.depth = data['geometry']['coordinates'][2]
        self.magnitude = data['properties']['mag']
        if type(self.magnitude) != float:
            if type(self.magnitude) != int:
                raise BadQuake()
        seconds_since_epoch = data['properties']['time'] / 1000.0
        time = datetime.datetime.fromtimestamp(seconds_since_epoch)
        self.year = time.year
        self.month = time.month
        self.day = time.day


class QuakeGroup:
    def __init__(self):
        self.size = 0
        self.vlist = None
        #self.labels = []
        self.alpha = 1.0

    def add_quake(self, q):
        self.size += 1
        x, y = lltoxy(q.longitude, q.latitude)
        #self.labels.append(
        #    pyglet.text.Label(q.title, x=x, y=y, color=(200,200,200,255)) )
        if self.vlist is None:
            self.vlist = pyglet.graphics.vertex_list(3,
                ('v2f', gen_vertices(q.longitude, q.latitude)),
                ('c4f', gen_color(q.magnitude, self.alpha)) )
        else:
            self.vlist.resize(self.vlist.get_size() + 3)
            vertices = gen_vertices(q.longitude, q.latitude)
            for i in range(0, len(vertices)):
                self.vlist.vertices[i - 6] = vertices[i]
            color = gen_color(q.magnitude, self.alpha)
            for i in range(0, len(color)):
                self.vlist.colors[i - 12] = color[i]

    def set_alpha(self, a):
        self.alpha = a
        i = 3
        while i < len(self.vlist.colors):
            self.vlist.colors[i] = self.alpha
            i += 4

    def draw(self):
        self.vlist.draw(GL_TRIANGLES)


class DrawManager:
    def __init__(self):
        self.quakes = {}

    def add_quake(self, q):
        if q.year not in self.quakes:
            self.quakes[q.year] = {}
        if q.month not in self.quakes[q.year]:
            self.quakes[q.year][q.month] = {}
        if q.day not in self.quakes[q.year][q.month]:
            self.quakes[q.year][q.month][q.day] = QuakeGroup()
        self.quakes[q.year][q.month][q.day].add_quake(q)

    def draw(self, date):
        days_prev = 80
        for i in range(0, days_prev + 1):
            alpha = 1.0 - (float(i) / float(days_prev))
            date_i = date - datetime.timedelta(i)
            try:
                self.quakes[date_i.year][date_i.month][date_i.day].set_alpha(alpha)
                self.quakes[date_i.year][date_i.month][date_i.day].draw()
            except KeyError:
                pass  # This is fine. No quakes on that date.


MIN_LONG = -180
MAX_LONG = 180
MIN_LAT = -90
MAX_LAT = 90
MIN_MAG = 6.0
MAX_MAG = 9.6

print('Loading earthquake data...')
data = json.loads(open('./USGS-quakes.json').read())
print('Earthquakes in dataset: ' + str(len(data['features'])))

print('Creating infographics...')
draw_manager = DrawManager()
winner = None
max_mag = 0
for i in range(0, len(data['features'])):
    try:
        quake = Quake(data['features'][i])
        draw_manager.add_quake(quake)
        if quake.magnitude > max_mag:
            winner = quake
            max_mag = quake.magnitude
    except BadQuake:
        print('We discarded an earthquake for having no magnitude.')
print('Beefiest earthquake ever: ' + winner.title)

WINDOW_W = (MAX_LONG - MIN_LONG) * SCALE
WINDOW_H = (MAX_LAT  - MIN_LAT) * SCALE
window = pyglet.window.Window(WINDOW_W, WINDOW_H)

glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


world_map = pyglet.sprite.Sprite(pyglet.image.load('bluemarble.jpg'))
world_map.scale = float(WINDOW_W) / float(world_map.image.width)


state_img = {
     1: pyglet.sprite.Sprite(pyglet.image.load('play.png')),
     0: pyglet.sprite.Sprite(pyglet.image.load('pause.png')),
    -1: pyglet.sprite.Sprite(pyglet.image.load('rewind.png'))
}
for i in range(-1,2):
    state_img[i].x = (WINDOW_W/2) - (state_img[i].width/2)
    state_img[i].y = (WINDOW_H/2) - (state_img[i].height/2)

state_img[0].opacity = 255
show_state = 0

info_label = pyglet.text.Label(
    'Use right, left, and space to play, rewind, and pause/unpause.',
    font_size=18,
    y=100,
    color=(200,200,200,255) )
info_label.x = WINDOW_W/2 - info_label.content_width/2


time_direction = 0
DAY_ELAPSE_FREQ = 0.04
timer = DAY_ELAPSE_FREQ

render_date = datetime.date(1900,1,1)
def get_date_str():
    global render_date, time_direction
    while True:
        try:
            return render_date.strftime('%m/%d/%Y')
        except ValueError:
            time_direction = 0
            render_date = datetime.date(1900,1,1)

date_label = pyglet.text.Label(
    get_date_str(),
    font_size=20,
    x=5,
    y=WINDOW_H-28,
    color=(200,200,200,255) )


@window.event
def on_draw():
    global date_label, render_date
    glClear(GL_COLOR_BUFFER_BIT)
    world_map.draw()
    draw_manager.draw(render_date)
    date_label.draw()
    if time_direction == 0:
        state_img[time_direction].draw()
        info_label.draw()
    elif show_state > 0:
        state_img[time_direction].opacity = show_state
        state_img[time_direction].draw()


@window.event
def on_key_press(k, modifiers):
    global time_direction, show_state
    if k == key.RIGHT:
        time_direction = 1
        show_state = 255
    elif k == key.LEFT:
        time_direction = -1
        show_state = 255
    elif k == key.SPACE:
        if time_direction == 0:
            time_direction = 1
            show_state = 255
        else:
            time_direction = 0


@window.event
def on_mouse_press(x, y, b, modifiers):
    global time_direction, show_state
    if b == mouse.LEFT:
        if time_direction == 0:
            time_direction = 1
            show_state = 255
        else:
            time_direction = 0


def update(dt):
    global render_date, timer, time_direction, show_state
    timer -= dt
    if show_state > 0:
        show_state = max(0, show_state - dt*150)
    while timer < 0.0:
        render_date += datetime.timedelta(time_direction)
        date_label.text = get_date_str()
        timer += DAY_ELAPSE_FREQ


pyglet.clock.schedule_interval(update,1/60.0)
pyglet.app.run()
