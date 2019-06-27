import dbus, dbus.mainloop.glib, sys
from gi.repository import GLib
import argparse
import requests
import bs4
import json
import subprocess
 
URL = 'https://www.google.com/search?tbm=isch&q='
HEADER = {'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
viewer = None
 
def show_album_art(artist, album, title):
    if artist == '' or album == '':
        return
 
    global viewer
    if viewer:
        viewer.terminate()
        viewer.kill()

    artist1 = artist
    album1 = album

 
    artist = '"' + '+'.join(artist.split()) + '"'
    album = '"' + '+'.join(album.split()) + '"'
    res = requests.get(URL+'+'.join((artist, album)), headers=HEADER)
    soup = bs4.BeautifulSoup(res.text, 'html.parser')
    meta_elements = soup.find_all("div", {"class": "rg_meta"})
    meta_dicts = (json.loads(e.text) for e in meta_elements)
 
    for d in meta_dicts:
        if d['oh'] == d['ow']:
            image_url = d['ou']
            break
 
    res = requests.get(image_url)
    if res.status_code != 200:
        return
 
    with open('album_art', 'wb') as f:
        f.write(res.content)
 
    viewer = subprocess.Popen(['feh', '-^ {} - {}'.format(artist1, title), '-Z', '-g', '440x440', 'album_art'])
 
def on_property_changed(interface, changed, invalidated):
    if interface != 'org.bluez.MediaPlayer1':
        return
    for prop, value in changed.iteritems():
        if prop == 'Status':
            print('Playback Status: {}'.format(value))
        elif prop == 'Track':
            print('Music Info:')
            for key in ('Title', 'Artist', 'Album'):
                print('   {}: {}'.format(key, value.get(key, '')))
            show_album_art(value.get('Artist', ''), value.get('Album', ''), value.get('Title', ''))
 
def on_playback_control(fd, condition):
    str = fd.readline()
    if str.startswith('play'):
        player_iface.Play()
    elif str.startswith('pause'):
        player_iface.Pause()
    elif str.startswith('next'):
        player_iface.Next()
    elif str.startswith('prev'):
        player_iface.Previous()
    return True
 
if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    obj = bus.get_object('org.bluez', "/")
    mgr = dbus.Interface(obj, 'org.freedesktop.DBus.ObjectManager')
    for path, ifaces in mgr.GetManagedObjects().iteritems():
        adapter = ifaces.get('org.bluez.MediaPlayer1')
        if not adapter:
            continue
        player = bus.get_object('org.bluez',path)
        player_iface = dbus.Interface(
                player,
                dbus_interface='org.bluez.MediaPlayer1')
        break
    if not adapter:
        sys.exit('Error: Media Player not found.')
 
    bus.add_signal_receiver(
            on_property_changed,
            bus_name='org.bluez',
            signal_name='PropertiesChanged',
            dbus_interface='org.freedesktop.DBus.Properties')
    GLib.io_add_watch(sys.stdin, GLib.IO_IN, on_playback_control)
    GLib.MainLoop().run()
