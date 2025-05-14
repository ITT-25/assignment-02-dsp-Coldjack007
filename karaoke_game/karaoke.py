import mido
import time
import pygame.midi
import pyglet
import threading
import audio_sample
import os
import sys

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'read_midi'))
sys.path.append(parent_dir)
import read_midi

SONG_MIDI_PATH = 'read_midi/berge.mid' # Will be overwritten from command line
FREQUENCY_DEVIATION_TOLERANCE = 1 # in Hz

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
WINDOW_PADDING = 10 # The entire screen should not be used, because it looks ugly

#The discrepancy between the lowest and highest note in the midi-file determines many values, such as the height of the player or music bricks.
WINDOW_HEIGHT_COMPUTATION_SPACE = WINDOW_HEIGHT - WINDOW_PADDING*2 # The actual height of the window used in computation
WINDOW_FREQUENCY_MINIMUM = 150 # Will be overwritten by the midi file
WINDOW_FREQUENCY_MAXIMUM = 320 # Will be overwritten by the midi file
WINDOW_FREQUENCY_SPECTRUM = WINDOW_FREQUENCY_MAXIMUM - WINDOW_FREQUENCY_MINIMUM # The frequency between the min and max frequency
WINDOW_PIXEL_PER_HERTZ_RATIO = WINDOW_HEIGHT_COMPUTATION_SPACE / WINDOW_FREQUENCY_SPECTRUM # A unit that depicts how many pixels should be used for 1Hz

MUSIC_BRICKS_HEIGHT = FREQUENCY_DEVIATION_TOLERANCE*2 * WINDOW_PIXEL_PER_HERTZ_RATIO
MUSIC_PIXEL_PER_SECOND_RATIO = 60 #Essentially determines the velocity of the music bricks
INITIAL_MUSIC_PADDING = 400 #To delay the game a bit, to give the player time to open the window

FRAMERATE = 60 #PCMasterRace

win = pyglet.window.Window(WINDOW_WIDTH, WINDOW_HEIGHT)

batch = pyglet.graphics.Batch()
PLAYER_PADDING = 20
player_brick = pyglet.shapes.Rectangle(PLAYER_PADDING,0,20,20,(255,0,0), batch=batch)

song = [] #notes read from the midi file
prepared_song = [] #notes with ids added
note_starts = [] #the start values of notes
note_ends = [] #the end values of notes
song_notes_to_sing = [] #the notes that are currently being sung
sung_note = 261
score = 0

music_brick_array = []

player_frequency = 200 #Is overwritten once the program runs

#UI
score_label = pyglet.text.Label("Dein Score ist 0", font_name="Times New Roman", x=WINDOW_WIDTH/2, y=WINDOW_HEIGHT-20, anchor_x="center", anchor_y="center", font_size=14)

game_state = "start" #"play", "end"

class Music_Brick:
    def __init__(self,x,y,width, height):
        self.x = x
        self.y = y
        self.sprite = pyglet.shapes.Rectangle(self.x, self.y, width, height, (0,255,0), batch=batch)

def declare_midi_file():
    global SONG_MIDI_PATH
    midi_file_path = input("Gib hier bitte eine Midi-Datei an: ")
    if not os.path.exists(midi_file_path) and not midi_file_path.lower().endswith(".mid"):
        print("Der Pfad existiert nicht oder ist keine Midi-Datei!")
        declare_midi_file()
    SONG_MIDI_PATH = midi_file_path
    
#Re-compute a lot of major values depending on the midi file provided, which makes the program's y axis dynamic
def init_min_max_window_frequency():
    global WINDOW_FREQUENCY_MINIMUM, WINDOW_FREQUENCY_MAXIMUM, WINDOW_PIXEL_PER_HERTZ_RATIO, WINDOW_FREQUENCY_SPECTRUM, MUSIC_BRICKS_HEIGHT, player_brick
    current_min_freq = 1000000 #outrageously large
    current_max_freq = 0
    for e in range(len(prepared_song)):
        num, start, end, current_freq = prepared_song[e]
        if current_freq > current_max_freq:
            current_max_freq = current_freq
        elif current_freq < current_min_freq and current_freq != 0:
            current_min_freq = current_freq
    WINDOW_FREQUENCY_MINIMUM = current_min_freq-WINDOW_PADDING
    WINDOW_FREQUENCY_MAXIMUM = current_max_freq+WINDOW_PADDING
    WINDOW_FREQUENCY_SPECTRUM = WINDOW_FREQUENCY_MAXIMUM - WINDOW_FREQUENCY_MINIMUM
    WINDOW_PIXEL_PER_HERTZ_RATIO = WINDOW_HEIGHT_COMPUTATION_SPACE / WINDOW_FREQUENCY_SPECTRUM
    MUSIC_BRICKS_HEIGHT = FREQUENCY_DEVIATION_TOLERANCE*2 * WINDOW_PIXEL_PER_HERTZ_RATIO
    player_brick.height = MUSIC_BRICKS_HEIGHT

def init_music_bricks():
    global prepared_song
    for id in range(len(prepared_song)):
        num, start, end, freq = prepared_song[id]
        brick_x = INITIAL_MUSIC_PADDING + start*MUSIC_PIXEL_PER_SECOND_RATIO
        brick_y = ((freq-WINDOW_FREQUENCY_MINIMUM)*WINDOW_PIXEL_PER_HERTZ_RATIO + WINDOW_PADDING)-FREQUENCY_DEVIATION_TOLERANCE
        brick_width = (end - start)*MUSIC_PIXEL_PER_SECOND_RATIO
        music_brick_array.append(Music_Brick(brick_x, brick_y, brick_width, MUSIC_BRICKS_HEIGHT))

#Fill all the necessary arrays from the midi file
def prepare_song():
    global song, prepared_song, note_starts, note_ends
    song = read_midi.midi_to_timecoded_frequencies(SONG_MIDI_PATH)
    prepared_song = add_note_id(song)
    init_min_max_window_frequency()
    note_starts = add_time_to_next_note_start(prepared_song)
    note_ends = add_time_to_next_note_end(prepared_song)
    init_music_bricks()
    play_song()

def add_note_id(song):
    song_with_note_ids = []
    for id in range(len(song)):
        start, end, freq = song[id]
        song_with_note_ids.append((id, start, end, freq))
    return song_with_note_ids

def add_time_to_next_note_start(song):
    song_with_time_to_next_note_start = []
    for i in range(len(song)):
        id, start, end, freq = song[i]
        if i < len(song) - 1:
            next_start = song[i + 1][1]
            time_to_next_note_start = next_start - start
        else:
            time_to_next_note_start = None 
        song_with_time_to_next_note_start.append((id, start, freq, time_to_next_note_start))
    return song_with_time_to_next_note_start

def add_time_to_next_note_end(song):
    song_sorted_by_note_end = sorted(song, key=lambda n: n[2])
    song_with_time_to_next_note_end = []
    for i in range(len(song_sorted_by_note_end)):
        id, start, end, freq = song_sorted_by_note_end[i]
        if i < len(song_sorted_by_note_end) - 1:
            next_end = song_sorted_by_note_end[i + 1][2]
            time_to_next_note_end = next_end - end
        else:
            time_to_next_note_end = None 
        song_with_time_to_next_note_end.append((id, end, time_to_next_note_end))
    return song_with_time_to_next_note_end

def play_song():
    global game_state
    game_state = "play"
    threading.Thread(target = evaluate_audio_input, daemon=True).start()
    threading.Thread(target = get_the_frequency, daemon=True).start()

    threading.Thread(target = add_notes_to_sing, daemon=True).start() #padding
    threading.Thread(target = remove_notes_to_sing, daemon=True).start() #padding
    threading.Thread(target = play_midi_file, daemon=True).start() #padding

def play_midi_file():
    global game_state
    pygame.midi.init()
    player = pygame.midi.Output(0)
    midi_file = mido.MidiFile(SONG_MIDI_PATH)
    current_time = 0
    time.sleep((INITIAL_MUSIC_PADDING-PLAYER_PADDING-player_brick.width)/MUSIC_PIXEL_PER_SECOND_RATIO)
    for msg in midi_file:
        if game_state != "play":
            return
        current_time += msg.time
        time.sleep(msg.time)

        if msg.type == 'note_on' and msg.velocity > 0:
            player.note_on(msg.note, msg.velocity)
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            player.note_off(msg.note, 0)
    player.close()
    game_state = "end"
    pygame.midi.quit()

#For the player input
def get_the_frequency():
    global player_frequency, player_brick, sung_note
    while game_state == "play":
        player_frequency = audio_sample.get_frequency()
        sung_note = player_frequency
        if player_frequency != 0 and player_frequency >= WINDOW_FREQUENCY_MINIMUM and player_frequency <= WINDOW_FREQUENCY_MAXIMUM:
            player_brick.y = WINDOW_PADDING + WINDOW_PIXEL_PER_HERTZ_RATIO*(player_frequency-WINDOW_FREQUENCY_MINIMUM)
            player_brick.color = (255,0,0)
        else:
            player_brick.color = (0,0,255)
        print("Your frequency: " +str(player_frequency))

def evaluate_audio_input():
    global score
    while game_state == "play":
        matching_note = next((n for n in song_notes_to_sing if abs(n[2] - sung_note) <= FREQUENCY_DEVIATION_TOLERANCE), None)
        if matching_note:
            score += 1
        time.sleep(0.01)

def add_notes_to_sing():
    time.sleep((INITIAL_MUSIC_PADDING-PLAYER_PADDING-player_brick.width)/MUSIC_PIXEL_PER_SECOND_RATIO)
    start_time = time.time()
    for note in note_starts:
        if game_state != "play":
            return
        while time.time() - start_time < note[1]:
            time.sleep(0.0001)
        song_notes_to_sing.append(note)
        print(f"START: {note}")

def remove_notes_to_sing():
    global game_state
    time.sleep((INITIAL_MUSIC_PADDING-PLAYER_PADDING-player_brick.width)/MUSIC_PIXEL_PER_SECOND_RATIO)
    while game_state == "play":
        start_time = time.time()
        for note in note_ends:
            if game_state != "play":
                return
            while time.time() - start_time < note[1]:
                time.sleep(0.0001)
            matching_note = next((n for n in song_notes_to_sing if n[0] == note[0]), None)
            if matching_note:
                song_notes_to_sing.remove(matching_note)
        print("PROZENT RICHTIG: " + str(score / note_ends[len(note_ends) - 1][1]))

def move_music_bricks(dt):
    global music_brick_array
    for e in range(len(music_brick_array)):
        music_brick_array[e].sprite.x -= dt*MUSIC_PIXEL_PER_SECOND_RATIO

@win.event
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.P:
        os._exit(0)

@win.event
def on_draw():
    win.clear()
    batch.draw()
    if note_ends:
        score_label.text = "Dein Score ist " + str(score / note_ends[len(note_ends) - 1][1])
        score_label.draw()

def main():
    declare_midi_file()
    prepare_song()
    pyglet.clock.schedule_interval(move_music_bricks, 1/FRAMERATE)
    pyglet.app.run()
    

if __name__ == "__main__":
    main()
