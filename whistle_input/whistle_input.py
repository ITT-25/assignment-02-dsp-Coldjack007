import pyglet
import audio_sample
import threading
import numpy as np
from scipy.stats import linregress
from pynput.keyboard import Controller, Key
import os

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

ICON_SIZE = 40
ICON_UNSELECTED_COLOR = (0,0,255)
ICON_SELECTED_COLOR = (255,0,0)
ICON_X = WINDOW_WIDTH/2 - ICON_SIZE/2
SPACE_SIZE = 5
ICON_NUMBER = int((WINDOW_HEIGHT-ICON_SIZE)/(ICON_SIZE+SPACE_SIZE))

current_frequency = 0
frequency_array = []
FREQUENCY_ARRAY_VALUE_MINIMUM = 8
ZERO_COUNTER_BREAKER = 10

keyboard = Controller()

win = pyglet.window.Window(WINDOW_WIDTH, WINDOW_HEIGHT)

class Icon:
    def __init__(self, number):
        self.number = number
        self.y = SPACE_SIZE + self.number*(ICON_SIZE+SPACE_SIZE)
        self.x = ICON_X
        self.selected = False
        self.sprite = pyglet.shapes.Rectangle(self.x, self.y, ICON_SIZE, ICON_SIZE, color=ICON_UNSELECTED_COLOR)

    def select(self, selected):
        global selected_icon
        if selected:
            self.selected = True
            self.sprite.color = ICON_SELECTED_COLOR
            selected_icon = self
        else:
            self.selected = False
            self.sprite.color = ICON_UNSELECTED_COLOR

icons = []
selected_icon = None

def init_icons():
    global icons
    for e in range(int(ICON_NUMBER)):
        icon = Icon(e)
        icons.append(icon)
    icons[0].select(True)

#direction: -1=down  1=up
def update_selection(direction):
    if direction == 1:
        if selected_icon.number < ICON_NUMBER-1:
            selected_icon.select(False)
            icons[selected_icon.number+1].select(True)
    if direction == -1:
        if selected_icon.number > 0:
            selected_icon.select(False)
            icons[selected_icon.number-1].select(True)


def start_frequency_thread():
    threading.Thread(target=get_the_frequency, daemon=True).start()

def get_the_frequency():
    global current_frequency, frequency_array
    zero_counter = 0 #zeroes represent no input
    while True:
        current_frequency = audio_sample.get_frequency()
        if current_frequency == 0:
            zero_counter += 1
            if zero_counter >= ZERO_COUNTER_BREAKER: #If the pause in audio input has been long enough...
                zero_counter = 0
                calculate_frequencies() # ...calculate the end result
        else:
            zero_counter = 0
            if frequency_array:
                if frequency_array[len(frequency_array)-1] != current_frequency: #To avoid too many repeat values that may skew calculation
                    frequency_array.append(current_frequency)
            else:
                frequency_array.append(current_frequency) #First input

def calculate_frequencies():
    global frequency_array
    if len(frequency_array) >= FREQUENCY_ARRAY_VALUE_MINIMUM:
        x = np.arange(len(frequency_array))
        slope, intercept, r_value, p_value, std_err = linregress(x, frequency_array) #Calculate upward or downward tendencies

        if slope > 0:
            #print("Die Zahlen steigen tendenziell.")
            update_selection(1)
            keyboard.tap(Key.up)
        elif slope < 0:
            #print("Die Zahlen fallen tendenziell.")
            update_selection(-1)
            keyboard.tap(Key.down)
        else:
            print("Keine Tendenz erkennbar.")
    else:
        print("Array wegen Inaktivität gelöscht.")
    print(frequency_array)
    frequency_array.clear()

@win.event
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.P:
        os._exit(0)

@win.event
def on_draw():
    win.clear()
    for e in icons:
        e.sprite.draw()

def main():
    start_frequency_thread()
    init_icons()
    pyglet.app.run()

if __name__ == "__main__":
    main()