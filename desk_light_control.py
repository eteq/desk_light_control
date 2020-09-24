#!/usr/bin/env python3

import json
import socket
import asyncio

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from pywizlight.bulb import wizlight as Wizlight, PilotBuilder

DEFAULT_COLORS = [(0, 255, 0), (255,150, 0), (255,0,0)]
DEFAULT_SCENE = 'Daylight'

DEFAULT_IP = ""
DEFAULT_PORT = 38899
DEFAULT_MAC = ""
TIMEOUT = 0.2

def turn_light_on(ip):
    light = Wizlight(ip, DEFAULT_PORT)
    asyncio.run(light.turn_on())

def turn_light_off(ip):
    light = Wizlight(ip, DEFAULT_PORT)
    asyncio.run(light.turn_off())

def turn_light_color(ip, rgb):
    light = Wizlight(ip, DEFAULT_PORT)
    asyncio.run(light.turn_on(PilotBuilder(rgb=rgb)))

def turn_light_scene(ip, scene):
    try:
        scene = int(scene)
    except ValueError:
        pass

    light = Wizlight(ip, DEFAULT_PORT)
    if isinstance(scene, str):
        sceneid = light.get_id_from_scene_name(scene)
    elif isinstance(scene, int):
        sceneid = scene
    else:
        raise TypeError('scene must be an int or str')
    asyncio.run(light.turn_on(PilotBuilder(scene=sceneid)))

def discover(verbose=True):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    message = r'{"method":"getSystemConfig","params":{}}'.encode()
    sock.sendto(message, ('<broadcast>', DEFAULT_PORT))

    sock.settimeout(TIMEOUT)

    responses = {}
    response = True
    while response:
        try:
            response, (ipaddr, port) = sock.recvfrom(2**16)
            if verbose:
                print('IP address', ipaddr, 'yielded', response)
            responses[ipaddr] = response
        except (BlockingIOError, socket.timeout) as e:
            response = None

    return responses




class MyWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Colorer")

        self.topbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.add(self.topbox)

        self.ip_box = Gtk.Box()
        self.ip_label = Gtk.Label()
        self.ip_label.set_text(' IP: ')
        self.ip_entry = Gtk.Entry()
        self.ip_entry.set_max_length(4*3+3)
        self.ip_entry.set_width_chars(self.ip_entry.get_max_length())
        self.ip_entry.set_text(DEFAULT_IP)
        self.ip_box.pack_start(self.ip_label, False, True, 0)
        self.ip_box.pack_start(self.ip_entry, True, True, 0)
        self.topbox.pack_start(self.ip_box, False, True, 0)

        self.discover_box = Gtk.Box()
        self.discover_button = Gtk.Button(label='Discover IPs')
        self.discover_button.connect("clicked", self.on_discover_button_clicked)
        self.mac_entry = Gtk.Entry()
        self.mac_entry.set_max_length(6*3)
        self.mac_entry.set_width_chars(self.mac_entry.get_max_length())
        self.mac_entry.set_text(DEFAULT_MAC)
        self.discover_box.pack_start(self.discover_button, False, True, 0)
        self.discover_box.pack_start(self.mac_entry, True, True, 0)
        self.topbox.pack_start(self.discover_box, False, True, 0)


        self.grid = Gtk.Grid()

        self.color_buttons = []
        self.color_set_buttons = []

        for i, c0 in enumerate(DEFAULT_COLORS):
            self.color_buttons.append(Gtk.ColorButton())
            self.color_buttons[-1].set_rgba(Gdk.RGBA(*c0, 1))
            self.color_set_buttons.append(Gtk.Button(label='Set Light'))

            self.color_set_buttons[-1].connect("clicked", self.on_set_button_clicked)

            self.grid.attach(self.color_buttons[-1], 0, i, 1, 1)
            self.grid.attach(self.color_set_buttons[-1], 1, i, 1, 1)

        # scene-setter
        self.scene_button = Gtk.Button(label='Set Scene')
        self.scene_button.connect("clicked", self.on_scene_button_clicked)
        self.scene_entry = Gtk.Entry()
        self.scene_entry.set_text(DEFAULT_SCENE)
        self.grid.attach(self.scene_button, 0, len(DEFAULT_COLORS)+1, 1, 1)
        self.grid.attach(self.scene_entry, 1, len(DEFAULT_COLORS)+1, 1, 1)

        self.topbox.pack_start(self.grid, True, True, 0)

        self.off_button = Gtk.Button(label='Light Off')
        self.off_button.connect("clicked", self.on_off_button_clicked)
        self.topbox.pack_start(self.off_button, False, True, 0)


    def on_set_button_clicked(self, widget):
        for i, w in enumerate(self.color_set_buttons):
            if w is widget:
                rgba = self.color_buttons[i].get_rgba()
                turn_light_color(self.ip_entry.get_text(),
                                 (rgba.red, rgba.green, rgba.blue))
                break
        else:
            assert False, 'The callback came from a widget that should not exist!'


    def on_scene_button_clicked(self, widget):
        turn_light_scene(self.ip_entry.get_text(), self.scene_entry.get_text())


    def on_off_button_clicked(self, widget):
        turn_light_off(self.ip_entry.get_text())


    def on_discover_button_clicked(self, widget):
        responses = discover()
        if self.mac_entry.get_text():
            mac_to_find = self.mac_entry.get_text().lower().replace(':', '')
            for ip, response in responses.items():
                response = json.loads(response)
                if response['result']['mac'] == mac_to_find:
                    print('Found mac', mac_to_find)
                    self.ip_entry.set_text(ip)
                    break
            else:
                print('Failed to find mac', mac_to_find)


win = MyWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()