#!/usr/bin/env python

from __future__ import division

ACTR6 = True
try:
    from actr6_jni import JNI_Server, VisualChunk, PAAVChunk
    from actr6_jni import Dispatcher as JNI_Dispatcher
    from actr6_jni import Pyglet_MPClock
except ImportError:
    ACTR6 = False

from pyglet import image, font, text, clock, resource
from pyglet.gl import *
from pyglet.window import key, FPSDisplay
from pyglet.image import SolidColorImagePattern

import os

import pygletreactor
pygletreactor.install()
from twisted.internet import reactor

from collections import deque

from cocos.euclid import *
from cocos.director import *
from cocos.layer import *
from cocos.sprite import *
from cocos.cocosnode import CocosNode
from cocos.menu import *
from cocos.text import *
from cocos.scenes.transitions import *
from cocos.actions.interval_actions import *
from cocos.actions.base_actions import *
from cocos.actions.instant_actions import * 
from cocos.actions.move_actions import *
from cocos.batch import BatchNode
from cocos.collision_model import *
import cocos.euclid as eu
from pyglet.media import StaticSource

from random import choice, randrange, uniform, sample, shuffle
import string

from primitives import Polygon, Rect

import platform

from util import hsv_to_rgb, screenshot
from handler import DefaultHandler
from menu import BetterMenu, GhostMenuItem, BetterEntryMenuItem
from scene import Scene

from odict import OrderedDict

try:
    from pyviewx.client import iViewXClient, Dispatcher
    from calibrator import CalibrationLayer, HeadPositionLayer
    eyetracking = True
except ImportError:
    eyetracking = False
    
from pycogworks.logging import get_time, Logger, writeHistoryFile, getDateTimeStamp
from pycogworks.crypto import rin2id
from cStringIO import StringIO
import tarfile
import json

class OptionsMenu(BetterMenu):

    def __init__(self):
        super(OptionsMenu, self).__init__('Options')
        self.screen = director.get_window_size()
        
        ratio = self.screen[1] / self.screen[0]
        
        self.select_sound = StaticSource(pyglet.resource.media('move.wav'))
        
        self.font_title['font_name'] = 'Pipe Dream'
        self.font_title['font_size'] = self.screen[0] / 18
        self.font_title['color'] = (255, 255, 255, 255)
        
        self.font_item['font_name'] = 'Pipe Dream',
        self.font_item['color'] = (255, 255, 255, 255)
        self.font_item['font_size'] = self.screen[1] / 16 * ratio
        self.font_item_selected['font_name'] = 'Pipe Dream'
        self.font_item_selected['color'] = (0, 0, 255, 255)
        self.font_item_selected['font_size'] = self.screen[1] / 16 * ratio
        
        self.items = OrderedDict()
        
        self.items['fps'] = ToggleMenuItem('Show FPS:', self.on_show_fps, director.show_FPS)
        self.items['fullscreen'] = ToggleMenuItem('Fullscreen:', self.on_fullscreen, director.window.fullscreen)
        if eyetracking:
            self.items['eyetracker'] = ToggleMenuItem("EyeTracker:", self.on_eyetracker, director.settings['eyetracker'])
            self.items['eyetracker_ip'] = EntryMenuItem('EyeTracker IP:', self.on_eyetracker_ip, director.settings['eyetracker_ip'])
            self.items['eyetracker_in_port'] = EntryMenuItem('EyeTracker In Port:', self.on_eyetracker_in_port, director.settings['eyetracker_in_port'])
            self.items['eyetracker_out_port'] = EntryMenuItem('EyeTracker Out Port:', self.on_eyetracker_out_port, director.settings['eyetracker_out_port'])
            self.set_eyetracker_extras(director.settings['eyetracker'])
        
        self.create_menu(self.items.values(), zoom_in(), zoom_out())
        
    def on_enter(self):
        super(OptionsMenu, self).on_enter()
        self.orig_values = (director.settings['eyetracker_ip'],
                            director.settings['eyetracker_in_port'],
                            director.settings['eyetracker_out_port'])
    
    def on_exit(self):
        super(OptionsMenu, self).on_exit()
        new_values = (director.settings['eyetracker_ip'],
                            director.settings['eyetracker_in_port'],
                            director.settings['eyetracker_out_port'])
        if new_values != self.orig_values:
            director.scene.dispatch_event("eyetracker_info_changed")
        
    def on_show_fps(self, value):
        director.show_FPS = value
        
    def on_fullscreen(self, value):
        screen = pyglet.window.get_platform().get_default_display().get_default_screen()
        director.window.set_fullscreen(value, screen)
    
    def on_experiment(self, value):
        director.settings['experiment'] = value
    
    if eyetracking:
    
        def set_eyetracker_extras(self, value):
            self.items['eyetracker_ip'].visible = value
            self.items['eyetracker_in_port'].visible = value
            self.items['eyetracker_out_port'].visible = value
            
        def on_eyetracker(self, value):
            director.settings['eyetracker'] = value
            self.set_eyetracker_extras(value)
            
        def on_eyetracker_ip(self, ip):
            director.settings['eyetracker_ip'] = ip
        
        def on_eyetracker_in_port(self, port):
            director.settings['eyetracker_in_port'] = port
        
        def on_eyetracker_out_port(self, port):
            director.settings['eyetracker_out_port'] = port
            
    def on_quit(self):
        self.parent.switch_to(0)

class MainMenu(BetterMenu):

    def __init__(self):
        super(MainMenu, self).__init__("Snake")
        self.screen = director.get_window_size()
        
        ratio = self.screen[1] / self.screen[0]
                
        self.select_sound = StaticSource(pyglet.resource.media('move.wav'))

        self.font_title['font_name'] = 'Pipe Dream'
        self.font_title['font_size'] = self.screen[0] / 18
        self.font_title['color'] = (255, 255, 255, 255)

        self.font_item['font_name'] = 'Pipe Dream',
        self.font_item['color'] = (255, 255, 255, 255)
        self.font_item['font_size'] = self.screen[1] / 16 * ratio
        self.font_item_selected['font_name'] = 'Pipe Dream'
        self.font_item_selected['color'] = (0, 0, 255, 255)
        self.font_item_selected['font_size'] = self.screen[1] / 16 * ratio

        self.menu_anchor_y = 'center'
        self.menu_anchor_x = 'center'

        self.items = OrderedDict()
        
        #self.items['mode'] = MultipleMenuItem('Mode: ', self.on_mode, director.settings['modes'], director.settings['modes'].index(director.settings['mode']))
        self.items['player'] = MultipleMenuItem('Player: ', self.on_player, director.settings['players'], director.settings['players'].index(director.settings['player']))
        # self.items['tutorial'] = MenuItem('Tutorial', self.on_tutorial)
        self.items['start'] = MenuItem('Start', self.on_start)
        self.items['options'] = MenuItem('Options', self.on_options)
        self.items['quit'] = MenuItem('Quit', self.on_quit)
        
        self.create_menu(self.items.values(), zoom_in(), zoom_out())

    def on_player(self, player):
        director.settings['player'] = director.settings['players'][player]

    def on_mode(self, mode):
        director.settings['mode'] = director.settings['modes'][mode]
    
    def on_tutorial(self):
        director.push(SplitColsTransition(Scene(TutorialLayer())))
        
    def on_options(self):
        self.parent.switch_to(1)
        
    def on_start(self):
        filebase = "Snake_%s" % (getDateTimeStamp())
        director.settings['filebase'] = filebase
        director.scene.dispatch_event('start_task')

    def on_quit(self):
        reactor.callFromThread(reactor.stop)
                
class ParticipantMenu(BetterMenu):

    def __init__(self):
        super(ParticipantMenu, self).__init__("Participant Information")
        self.screen = director.get_window_size()
        
        ratio = self.screen[1] / self.screen[0]
                
        self.select_sound = StaticSource(pyglet.resource.media('move.wav'))

        self.font_title['font_name'] = 'Pipe Dream'
        self.font_title['font_size'] = self.screen[0] / 18
        self.font_title['color'] = (255, 255, 255, 255)

        self.font_item['font_name'] = 'Pipe Dream',
        self.font_item['color'] = (255, 255, 255, 255)
        self.font_item['font_size'] = self.screen[1] / 16 * ratio
        self.font_item_selected['font_name'] = 'Pipe Dream'
        self.font_item_selected['color'] = (0, 0, 255, 255)
        self.font_item_selected['font_size'] = self.screen[1] / 16 * ratio

        self.menu_anchor_y = 'center'
        self.menu_anchor_x = 'center'

    def on_enter(self):
        super(ParticipantMenu, self).on_enter()
        self.items = OrderedDict()
        self.items['firstname'] = BetterEntryMenuItem('First Name:', self.on_info_change, "", validator=lambda x: x.isalpha())
        self.items['lastname'] = BetterEntryMenuItem('Last Name:', self.on_info_change, "", validator=lambda x: x.isalpha())
        self.items['rin'] = BetterEntryMenuItem('RIN:', self.on_info_change, "", max_length=9, validator=lambda x: unicode(x).isnumeric())
        self.items['start'] = MenuItem('Start', self.on_start)
        self.create_menu(self.items.values(), zoom_in(), zoom_out())
        self.items['start'].visible = False
        
    def on_exit(self):
        super(ParticipantMenu, self).on_exit()
        for c in self.get_children(): self.remove(c)
                
    def on_info_change(self, *args, **kwargs):
        firstname = ''.join(self.items['firstname']._value).strip()
        lastname = ''.join(self.items['lastname']._value).strip()
        rin = ''.join(self.items['rin']._value)
        if len(firstname) > 0 and len(lastname) > 0 and len(rin) == 9:
            self.items['start'].visible = True
        else:
            self.items['start'].visible = False
        
    def on_start(self):
        si = {}
        si['first_name'] = ''.join(self.items['firstname']._value).strip()
        si['last_name'] = ''.join(self.items['lastname']._value).strip()
        si['rin'] = ''.join(self.items['rin']._value)
        si['encrypted_rin'], si['cipher'] = rin2id(si['rin'])
        si['timestamp'] = getDateTimeStamp()
        director.settings['si'] = si
        filebase = "WilliamsSearch_%s_%s" % (si['timestamp'], si['encrypted_rin'][:8])
        director.settings['filebase'] = filebase
        writeHistoryFile("data/%s.history" % filebase, si)
        director.scene.dispatch_event('start_task')

    def on_quit(self):
        self.parent.switch_to(0)
        
class BackgroundLayer(Layer):
    
    def __init__(self):
        super(BackgroundLayer, self).__init__()
        self.screen = director.get_window_size()
        img = resource.image('background.jpg')
        if self.screen[0] > 1600:
            scale = max(self.screen[0]/1600,self.screen[1]/1000)
        elif self.screen[0] < 1600:
            scale = min(self.screen[0]/1600,self.screen[1]/1000)
        s = Sprite(img,position=(self.screen[0]/2,self.screen[1]/2),scale=scale)
        self.add(s)
        self.add(ColorLayer(0,0,0,128),z=1)

class TaskBackground(Layer):
    
    def __init__(self):
        self.screen = director.get_window_size()
        super(TaskBackground, self).__init__()
        img = resource.image('background.jpg')
        if self.screen[0] > 1600:
            scale = max(self.screen[0]/1600,self.screen[1]/1000)
        elif self.screen[0] < 1600:
            scale = min(self.screen[0]/1600,self.screen[1]/1000)
        s = Sprite(img,position=(self.screen[0]/2,self.screen[1]/2),scale=scale)
        self.add(s)
        self.add(ColorLayer(128,128,128,128),z=1)
        
def grid2coord(c, r, cell, pad=1):
        x = (c - .5) * cell + c + pad
        y = (r - .5) * cell + r + pad
        return((x,y))
        
class GridSquare(Sprite):
    
    def __init__(self, c, r, size, opacity=255, color=(255, 255, 255)):
        self.grid_loc = (c, r)
        self.size = size
        img = SolidColorImagePattern((255,255,255,255)).create_image(size, size)
        super(GridSquare, self).__init__(img, position=grid2coord(c, r, size), color=color, opacity=opacity)
        
    def set_grid_loc(self, (c, r)):
        self.grid_loc = (c, r)
        self.position = grid2coord(c, r, self.size)
        
    def set_grid_loc_rel(self, (c, r)):
        self.set_grid_loc((self.grid_loc[0]+c, self.grid_loc[1]+r))
        
class MoveWithCallback(MoveBy):
    
    def init(self, delta, cb):
        MoveBy.init(self, delta, 0)
        self.cb = cb

    def start(self):
        MoveBy.start(self)
        self.cb()
    
class Task(ColorLayer, pyglet.event.EventDispatcher):
    
    d = Dispatcher()
    actr_d = JNI_Dispatcher()
    
    states = ["INIT", "WAIT_ACTR_CONNECTION", "WAIT_ACTR_MODEL", "CALIBRATE", 
              "IGNORE_INPUT", "PLAY", "GAME_OVER"]
    STATE_INIT = 0
    STATE_WAIT_ACTR_CONNECTION = 1
    STATE_WAIT_ACTR_MODEL = 2
    STATE_CALIBRATE = 3
    STATE_IGNORE_INPUT = 4
    STATE_PLAY = 5
    STATE_GAME_OVER = 6
    
    is_event_handler = True
    
    def __init__(self, client, actr):
        self.screen = director.get_window_size()
        self.ncells = 41
        self.cell = int(self.screen[1] / self.ncells * .1) * 10
        width = self.ncells * self.cell + self.ncells + 1
        
        super(Task, self).__init__(0, 0, 0, 255, width, width)
        self.position = ((self.screen[0]-width)/2, (self.screen[1]-width)/2)
        
        self.state = self.STATE_INIT
        
        self.snake = None
        self.food = None
        
        self.blop = StaticSource(pyglet.resource.media('blop.mp3'))
        self.laugh = StaticSource(pyglet.resource.media('laugh.mp3'))
        
        self.text_batch = BatchNode()
        self.game_over_label = text.Label("GAME OVER", font_size=int(self.cell*4),
                                          x= width / 2, y= width / 2, font_name="Pipe Dream",
                                          color=(255,255,255,255), anchor_x='center', anchor_y='bottom',
                                          batch=self.text_batch.batch)
        self.game_over_label = text.Label("Press Spacebar For New Game", font_size=int(self.cell*2),
                                          x= width / 2, y= width / 2, font_name="Pipe Dream",
                                          color=(255,255,255,255), anchor_x='center', anchor_y='top',
                                          batch=self.text_batch.batch)
        
    def get_move_by(self):
        if self.movement_direction == 1:
            return (0, 1)
        elif self.movement_direction == 2:
            return (1, 0)
        elif self.movement_direction == 3:
            return (0, -1)
        elif self.movement_direction == 4:
            return (-1, 0)
        
    def move_snake_body(self):
        mod = self.get_move_by()
        c,r = self.snake[0].grid_loc
        nc = c + mod[0]
        nr = r + mod[1]
        if (nc,nr) == self.food.grid_loc:
            self.blop.play()
            self.remove(self.food)
            self.snake.insert(1,GridSquare(c, r, self.cell))
            self.add(self.snake[1])
            self.spawn_food()
            self.speed = self.speed * .99
        elif nc < 1 or nc > self.ncells or nr < 1 or nr > self.ncells:
            self.game_over()
            return
        else:
            for i in range(1,len(self.snake))[::-1]:
                self.snake[i].set_grid_loc(self.snake[i-1].grid_loc)
        self.snake[0].set_grid_loc((nc,nr))
        for i in range(1,len(self.snake)):
            if self.snake[0].grid_loc == self.snake[i].grid_loc:
                self.game_over()
                return
        self.snake[0].do(Delay(self.speed) + CallFunc(self.move_snake_body))
        self.ready = True
        
    def game_over(self):
        self.laugh.play()
        self.state = self.STATE_GAME_OVER
        self.snake[0].stop()
        self.ready = False
        if self.snake:
            map(self.remove, self.snake)
        if self.food:
            self.remove(self.food)
        self.add(self.text_batch, z=1)
        
    def spawn_food(self):
        cont = True
        while cont:
            cont = False
            c = (choice(range(0, self.ncells)) + 1)
            r = (choice(range(0, self.ncells)) + 1)
            for s in self.snake:
                if s.grid_loc == (c,r):
                    cont = True
                    break
            if not cont:
                self.food = GridSquare(c, r, self.cell, color=(255, 0, 0))
                self.add(self.food)
        
    def reset(self):
        self.movement_direction = 1
        self.speed = .1
        
        center = int(self.ncells/2) + 1
        self.snake = [GridSquare(center, center, self.cell)]
        self.add(self.snake[0])
        
        for r in range(1, 3):
            self.snake.append(GridSquare(center, center-r, self.cell))
            self.add(self.snake[-1])
            
        self.spawn_food()
        
        self.state = self.STATE_PLAY
        self.snake[0].do(Delay(2) + CallFunc(self.move_snake_body))
        
    def on_enter(self):
        if isinstance(director.scene, TransitionScene): return        
        super(Task, self).on_enter()
        self.reset()
        
    def on_exit(self):
        if isinstance(director.scene, TransitionScene): return
        super(Task, self).on_exit()
        
    if ACTR6:
        @actr_d.listen('connectionMade')
        def ACTR6_JNI_Event(self, model, params):
            pass
            
        @actr_d.listen('connectionLost')
        def ACTR6_JNI_Event(self, model, params):
            pass
            
        @actr_d.listen('reset')
        def ACTR6_JNI_Event(self, model, params):
            pass
            
        @actr_d.listen('model-run')
        def ACTR6_JNI_Event(self, model, params):
            pass
            
        @actr_d.listen('model-stop')
        def ACTR6_JNI_Event(self, model, params):
            pass

        @actr_d.listen('gaze-loc')
        def ACTR6_JNI_Event(self, model, params):
            pass
            
        @actr_d.listen('attention-loc')
        def ACTR6_JNI_Event(self, model, params):
            pass

        @actr_d.listen('keypress')
        def ACTR6_JNI_Event(self, model, params):
            pass

        @actr_d.listen('mousemotion')
        def ACTR6_JNI_Event(self, model, params):
            pass

        @actr_d.listen('mouseclick')
        def ACTR6_JNI_Event(self, model, params):
            pass
    
    if eyetracking:
        @d.listen('ET_FIX')
        def iViewXEvent(self, inResponse):
            pass
            
        @d.listen('ET_SPL')
        def iViewXEvent(self, inResponse):
            pass
        
    def on_mouse_press(self, x, y, buttons, modifiers):
        pass

    def on_mouse_motion(self, x, y, dx, dy):
        pass
        
    def on_key_press(self, symbol, modifiers):
        if self.state == self.STATE_PLAY:
            if self.ready:
                self.ready = False
                if symbol == key.UP:
                    if self.movement_direction == 2 or self.movement_direction == 4:
                        self.movement_direction = 1
                elif symbol == key.DOWN:
                    if self.movement_direction == 2 or self.movement_direction == 4:
                        self.movement_direction = 3
                elif symbol == key.RIGHT:
                    if self.movement_direction == 1 or self.movement_direction == 3:
                        self.movement_direction = 2
                elif symbol == key.LEFT:
                    if self.movement_direction == 1 or self.movement_direction == 3:
                        self.movement_direction = 4
        elif self.state == self.STATE_GAME_OVER:
            if symbol == key.SPACE:
                self.remove(self.text_batch)
                self.reset()
                    
class ACTRScrim(ColorLayer):
    
    def __init__(self):
        self.screen = director.get_window_size()
        super(ACTRScrim, self).__init__(255, 0, 0, 255, self.screen[0], self.screen[1])
        
        self.wait_connection = Label("Waiting for connection from ACT-R",
                                     position=(self.width / 2, self.height / 5 * 2),
                                     font_name='Pipe Dream', font_size=24,
                                     color=(0, 0, 0, 255), anchor_x='center', anchor_y='center')
        
        self.wait_model = Label("Waiting for ACT-R model to run",
                                     position=(self.width / 2, self.height / 5 * 2),
                                     font_name='Pipe Dream', font_size=24,
                                     color=(0, 0, 0, 255), anchor_x='center', anchor_y='center')
        
        self.spinner = Sprite(resource.image('spinner.png'), 
                              position=(self.width / 2, self.height / 5 * 3), 
                              color=(255, 255, 255))
        self.spinner.do(Repeat(RotateBy(360, 1)))
        
        self.setWaitConnection()
        
    def setWaitConnection(self):
        for c in self.get_children(): self.remove(c)
        self.add(self.spinner)
        self.add(self.wait_connection)
        self.color = (255,0,0)
        
    def setWaitModel(self):
        for c in self.get_children(): self.remove(c)
        self.add(self.spinner)
        self.add(self.wait_model)
        self.color = (0,255,0)
            
class EyetrackerScrim(ColorLayer):
    
    def __init__(self):
        self.screen = director.get_window_size()
        super(EyetrackerScrim, self).__init__(0, 0, 0, 224, self.screen[0], self.screen[1])
        l = Label("Reconnecting to eyetracker...", position=(self.screen[0] / 2, self.screen[1] / 2), font_name='', font_size=32, bold=True, color=(255, 255, 255, 255), anchor_x='center', anchor_y='center')
        self.add(l)

class SnakeEnvironment(object):
    
    title = "Snake"
        
    def __init__(self):
        
        if not os.path.exists("data"): os.mkdir("data")
        
        pyglet.resource.path.append('resources')
        pyglet.resource.reindex()
        pyglet.resource.add_font('Pipe_Dream.ttf')
        
        p = pyglet.window.get_platform()
        d = p.get_default_display()
        s = d.get_default_screen()
        
        director.init(width=s.width, height=s.height,
                  caption=self.title, visible=False, resizable=True)
        director.window.set_size(int(s.width * .75), int(s.height * .75))
        
        director.window.pop_handlers()
        director.window.push_handlers(DefaultHandler())
            
        director.settings = {'eyetracker': True,
                             'eyetracker_ip': '127.0.0.1',
                             'eyetracker_out_port': '4444',
                             'eyetracker_in_port': '5555',
                             'player': 'Human',
                             'players': ['Human']}
        
        self.client = None
        self.client_actr = None
        
        if ACTR6:
            director.settings['players'].append("ACT-R")
            #director.settings['player'] = "ACT-R"
            director.settings['eyetracker'] = False
            self.client_actr = JNI_Server(self)
            self.listener_actr = reactor.listenTCP(6666, self.client_actr)
        elif eyetracking:
            self.client = iViewXClient(director.settings['eyetracker_ip'], int(director.settings['eyetracker_out_port']))
            self.listener = reactor.listenUDP(int(director.settings['eyetracker_in_port']), self.client) 
        
        director.fps_display = clock.ClockDisplay(font=font.load('', 18, bold=True))
        #fps_display = FPSDisplay(director.window)
        #fps_display.label.font_size = 12
        #director.fps_display = fps_display

        director.set_show_FPS(True)
        director.window.set_fullscreen(False)
        director.window.set_mouse_visible(False)
        
        if platform.system() != 'Windows':
            director.window.set_icon(pyglet.resource.image('logo.png'))
        
        # Intro scene and its layers        
        self.introScene = Scene()
                    
        self.mainMenu = MainMenu()
        self.optionsMenu = OptionsMenu()
        self.participantMenu = ParticipantMenu()
        self.introBackground = BackgroundLayer()
        self.eyetrackerScrim = EyetrackerScrim()
        
        self.introScene.add(self.introBackground)
        self.mplxLayer = MultiplexLayer(self.mainMenu, self.optionsMenu, self.participantMenu)
        self.introScene.add(self.mplxLayer, 1)
        
        self.introScene.register_event_type('start_task')
        self.introScene.register_event_type('eyetracker_info_changed')
        self.introScene.push_handlers(self)
        
        # Task scene and its layers
        self.taskScene = Scene()
        
        self.taskBackgroundLayer = TaskBackground()
        self.taskLayer = Task(self.client, self.client_actr)
        self.actrScrim = ACTRScrim()
        
        if self.client:
            self.calibrationLayer = CalibrationLayer(self.client)
            self.calibrationLayer.register_event_type('show_headposition')
            self.calibrationLayer.register_event_type('hide_headposition')
            self.calibrationLayer.push_handlers(self)
            self.headpositionLayer = HeadPositionLayer(self.client)
        
        self.taskLayer.register_event_type('new_trial')
        self.taskLayer.push_handlers(self.taskBackgroundLayer)
        self.taskLayer.register_event_type('start_calibration')
        self.taskLayer.register_event_type('stop_calibration')
        self.taskLayer.register_event_type('show_headposition')
        self.taskLayer.register_event_type('hide_headposition')
        self.taskLayer.register_event_type('actr_wait_connection')
        self.taskLayer.register_event_type('actr_wait_model')
        self.taskLayer.register_event_type('actr_running')
        self.taskLayer.push_handlers(self)
        
        self.taskScene.add(self.taskBackgroundLayer)
        self.taskScene.add(self.taskLayer, 1)
        self.actrScrim.visible = False
        self.taskScene.add(self.actrScrim, 3)
        
        self.taskScene.register_event_type('show_intro_scene')
        self.taskScene.push_handlers(self)
            
        director.window.set_visible(True)
    
    def actr_wait_connection(self):
        self.actrScrim.setWaitConnection()
        self.actrScrim.visible = True
        
    def actr_wait_model(self):
        self.actrScrim.setWaitModel()
        self.actrScrim.visible = True
    
    def actr_running(self):
        self.actrScrim.visible = False

    def start_calibration(self, on_success, on_failure):
        self.calibrationLayer.on_success = on_success
        self.calibrationLayer.on_failure = on_failure
        self.taskScene.add(self.calibrationLayer, 2)
        
    def stop_calibration(self):
        self.taskScene.remove(self.calibrationLayer)
    
    def show_headposition(self):
        self.taskScene.add(self.headpositionLayer, 3)
        
    def hide_headposition(self):
        self.taskScene.remove(self.headpositionLayer)
        
    def eyetracker_listen(self, _):
        self.listener = reactor.listenUDP(int(director.settings['eyetracker_in_port']), self.client)
        self.introScene.remove(self.eyetrackerScrim)
        self.introScene.enable_handlers(True)
        
    def eyetracker_info_changed(self):
        if self.client.remoteHost != director.settings['eyetracker_ip'] or \
        self.client.remotePort != int(director.settings['eyetracker_out_port']):
            self.client.remoteHost = director.settings['eyetracker_ip']
            self.client.remotePort = int(director.settings['eyetracker_out_port'])
        else:
            self.introScene.add(self.eyetrackerScrim, 2)
            self.introScene.enable_handlers(False)
            d = self.listener.stopListening()
            d.addCallback(self.eyetracker_listen)
        
    def show_intro_scene(self):
        self.mplxLayer.switch_to(0)
        director.replace(self.introScene)
        
    def start_task(self):
        director.replace(SplitRowsTransition(self.taskScene))
                 
def main():
    snake = SnakeEnvironment()
    snake.show_intro_scene()
    reactor.run()
