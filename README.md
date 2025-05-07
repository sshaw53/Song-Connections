# Artist Collaboration Path Finder by Sierra Shaw

My project aims to find the shortest collaboration path between two artists based on their shared songs. It uses the Spotify Web API (from the `spotipy` Python library) to build a collaboration graph, where each node is an artist and the edges connect artists that have co-released a song or track.

## Project Overview

Given two artist names, my program will:
1. Find each artist's collaborators by going through the songs on their albums and singles.
2. Create a graph using this data.
3. Apply **bidirectional BFS** to find the shortest path between the two artists through artist connections.
4. Displays the artist path along with the shared song that links each pair visually on a frontend.

To improve the performance of my algorithm and reduce the number of API calls, my project also implements a **caching system** using a local JSON file which stores collaborator data from previously searched artists.

## Technologies Used

- **Spotify Web API** via [`spotipy`] on Python
- **Python libraries**: `collections`, `json`, `os`, `deque`

## Algorithms & Data Structures

### Main Algorithm:
- **Bidirectional BFS**: Reduces the depth of the BFS tree searching by simultaneously searching from both the start and end artists. This results in faster execution than standard BFS for large graphs.

### Data Structures:
- **Graph / Map**: Each artist is a node and edges exists between two artists if they appear on a song together.
- **`dict` of `set`s**: Used to cache collaborator relationships, makes for faster lookups and reduces Spotify API calls when it saves to the file.
- **`deque`**: Queue used for BFS traversal.
- **`dict`**: Used to track visited nodes and paths from both directions.

## Time Complexity

Time complexity of key methods:

- **`get_collaborators(artist_id)`**:  
  - Worst-case: **O(n * m)** where `n` is the number of albums (limit= 50 per call) and `m` is the number of tracks per album.  
  - This is where the most calls to Spotify's API happen, which is why I tried to decrease it by caching to a file.

- **`bidirectional_bfs(start_id, end_id)`**:  
  - In terms of graph nodes: **O(b^(d/2))** where `b` is branching factor and `d` is depth of shortest path.  
  - This runs much faster than regular BFS which runs in **O(b^d)**.

- **`expand_layer()`** (called by `bidirectional_bfs`): 
  - Each call looks at a layer of collaborators: **O(k)** where `k` is the number of collaborators for the artist at the current level.

- **`get_shared_songs()`**:  
  - API call with fixed limit (1): **O(1)** because I only wanted to find one song between the two artists.

- **`print_path_with_songs()`**:  
  - Linear in path length `p`: **O(p)** gets names and shared songs, often very short.

- **`load_cache()` / `save_cache()`**:  
  - JSON --> Python and vice versa of a JSON dictionary with `n` entries: **O(n)**.
