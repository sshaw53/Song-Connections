import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import deque
import json
import os

# Setting up Spotify to collect data
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id='49a2e5f41e6549979db0f2848bd84f08',
    client_secret='1f8115a028f34de29dd75d9c3c890062'
))

# Cache handling - preventing an overload of Spotify API calls by saving to a file on my computer
# Stores which artists have which collaborators
collaborator_cache = {}

# Loads my current file into memory & converts the file containing a dict of lists to a Python dict of sets
def load_cache(filename="artist_cache.json"):
    global collaborator_cache
    if os.path.exists(filename):
        with open(filename, "r") as f:
            data = json.load(f)
            collaborator_cache = {k: set(v) for k, v in data.items()}
        
        # Update the number of loading from file 
        print(f"Loaded {len(collaborator_cache)} artists from cache.")
    else:
        print("No cache found, starting fresh.")

# Converts back to lists
def save_cache(filename="artist_cache.json"):
    with open(filename, "w") as f:
        json.dump({k: list(v) for k, v in collaborator_cache.items()}, f)
    # Update the number of added artists to file 
    print(f"Saved {len(collaborator_cache)} artists to cache.")

# Utilizing Spotify API
def get_artist_id(artist_name):
    result = sp.search(q='artist:' + artist_name, type='artist', limit=1)
    items = result['artists']['items']
    # Must get their ID number because the API looks for ID numbers not artist's names
    return items[0]['id'] if items else None

# For display
def get_artist_name(artist_id):
    return sp.artist(artist_id)['name']

# Finds collaborators from top tracks and saves to cache
def get_collaborators(artist_id):
    if artist_id in collaborator_cache:
        return collaborator_cache[artist_id]
    
    # Collaborators are being stored in a set
    collaborators = set()
    try:
        # Looking at all potential collaborators rather than top tracks - setting a limit bc that's Spotify's max album limit
        albums = []
        results = sp.artist_albums(artist_id, album_type='album,single', limit=50)
        albums.extend(results['items'])
        while results['next']:
            results = sp.next(results)
            albums.extend(results['items'])

        album_ids = list({album['id'] for album in albums})

        for album_id in album_ids:
            try:
                tracks = sp.album_tracks(album_id)
                for track in tracks['items']:
                    track_artist_ids = [a['id'] for a in track['artists']]
                    # Only if the current artist is on the track (had previous issues with finding non collaborators)
                    if artist_id in track_artist_ids:
                        for aid in track_artist_ids:
                            if aid != artist_id:
                                collaborators.add(aid)
            
            # Debugging
            except Exception as e:
                print(f"Error reading album {album_id}: {e}")

        collaborator_cache[artist_id] = collaborators
    except Exception as e:
        print(f"Error fetching albums for {artist_id}: {e}")
        collaborator_cache[artist_id] = set()

    return collaborators

# Using BFS from both directions to reduce the size and length of the trees
def bidirectional_bfs(start_id, end_id):
    # If we've found the middle point where the artists meet we've found our path
    if start_id == end_id:
        return [start_id]

    # Using a double-ended queue because very efficient for BFS queues (goes form both artists)
    forward_queue = deque([(start_id, [start_id])])
    backward_queue = deque([(end_id, [end_id])])

    # Visited maps to see what each artist has seen
    forward_visited = {start_id: [start_id]}
    backward_visited = {end_id: [end_id]}

    while forward_queue and backward_queue:
        # Expand the smaller queue always
        if len(forward_queue) <= len(backward_queue):
            result = expand_layer(forward_queue, forward_visited, backward_visited)
        else:
            result = expand_layer(backward_queue, backward_visited, forward_visited, reverse=True)
        if result:
            return result
    return None

# A singular layer of BFS
def expand_layer(queue, this_visited, other_visited, reverse=False):
    # For every node, look at collaborators
    for _ in range(len(queue)):
        current_id, path = queue.popleft()
        for neighbor_id in get_collaborators(current_id):
            # For new collaborators, extend the path and add them to the queue
            if neighbor_id in this_visited:
                continue
            new_path = path + [neighbor_id]
            this_visited[neighbor_id] = new_path
            queue.append((neighbor_id, new_path))

            # If we've found a collaborator that's already visited on the other side, we found our connection
            if neighbor_id in other_visited:
                other_path = other_visited[neighbor_id]
                # Merge the path properly                
                if reverse:
                    return other_path + new_path[::-1][1:]
                else:
                    return path + other_path[::-1][1:]
    return None

# Once we have the path, finding shared songs to create the song connection between each path
def get_shared_songs(artist_id_1, artist_id_2):
    name_1 = get_artist_name(artist_id_1)
    name_2 = get_artist_name(artist_id_2)
    query = f'artist:"{name_1}" artist:"{name_2}"'

    try:
        # Get a single song that connects 2 artists
        results = sp.search(q=query, type='track', limit=1)
        tracks = results['tracks']['items']
        return [tracks[0]['name']] if tracks else []
    except Exception as e:
        print(f"Error searching for shared songs between {name_1} and {name_2}: {e}")
        return []

# Displaying the path, as well as the songs that connect on the path
def print_path_with_songs(id_path):
    print("\nCollaboration Path:")
    for i in range(len(id_path)):
        print(get_artist_name(id_path[i]), end='')
        if i < len(id_path) - 1:
            print(" → ", end='')
    print("\n\nShared Song Between Each Pair:")

    for i in range(len(id_path) - 1):
        a1, a2 = id_path[i], id_path[i + 1]
        name1, name2 = get_artist_name(a1), get_artist_name(a2)
        shared = get_shared_songs(a1, a2)

        print(f"\n{name1} ↔ {name2}:")
        if shared:
            print(f"   {shared[0]}")
        else:
            print("   No shared song found.")

# Gets the path by calling sub functions & printing for GUI
def find_collab_path(name1, name2):
    id1 = get_artist_id(name1)
    id2 = get_artist_id(name2)
    
    # Checks for identification of artist ID's
    if not id1 or not id2:
        return None, "One or both artists not found."
    
    # Calls the double BFS function    
    path = bidirectional_bfs(id1, id2)
    if not path:
        return None, "No path found."
    
    output = "Artist Collaboration Path:\n\n"
    for i in range(len(path)):
        output += f"{i+1}. {get_artist_name(path[i])}\n"
        if i < len(path) - 1:
            output += "   -->\n"

    output += "\nShared Songs Between Each Pair:\n"
    for i in range(len(path) - 1):
        a1, a2 = path[i], path[i + 1]
        name1, name2 = get_artist_name(a1), get_artist_name(a2)
        songs = get_shared_songs(a1, a2)
        song_display = songs[0].replace("’", "'") if songs else "No shared song"
        output += f"- {name1} <--> {name2}: {song_display}\n"
    
    return output

# ---------- GUI ----------

import os
os.environ["PYDEVD_USE_FRAME_EVAL"] = "NO"

import dearpygui.dearpygui as dpg
def visualize_path(sender, app_data):
    artist1 = dpg.get_value("artist_1_input")
    artist2 = dpg.get_value("artist_2_input")
    dpg.set_value("path_output", "Searching...")
    result = find_collab_path(artist1, artist2)
    dpg.set_value("path_output", result)
    save_cache()

# Setup
load_cache()

dpg.create_context()
dpg.create_viewport(title='Song Connections', width=1000, height=600)
dpg.set_viewport_clear_color((255, 255, 255, 255))

with dpg.window(
    label="Overlay", 
    no_title_bar=True, 
    no_background=True, 
    no_move=True, 
    no_resize=True, 
    no_scrollbar=True, 
    no_collapse=True,
    width=1000, 
    height=600
):
    dpg.add_spacer(height=80)
    dpg.add_text("Enter two artists to find their collaboration path:", color=(0, 0, 0))
    dpg.add_spacer(height=15)

    with dpg.group(horizontal=True):
        dpg.add_input_text(label="", hint="Artist 1", width=300, tag="artist_1_input", on_enter=True, callback=visualize_path)
        dpg.add_spacer(width=50)
        dpg.add_input_text(label="", hint="Artist 2", width=300, tag="artist_2_input", on_enter=True, callback=visualize_path)

    dpg.add_spacer(height=20)
    dpg.add_button(label="Find Connection", callback=visualize_path)

    dpg.add_spacer(height=30)
    dpg.add_text("", tag="path_output", wrap=800, color=(0, 0, 0))

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
