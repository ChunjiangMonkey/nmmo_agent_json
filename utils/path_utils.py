import heapq
import numpy as np
from nmmo.lib.utils import in_bounds

AREA_TABLE = {
    (0, 0): "northwest",
    (0, 1): "north",
    (0, 2): "northeast",
    (1, 0): "west",
    (1, 1): "center",
    (1, 2): "east",
    (2, 0): "southwest",
    (2, 1): "south",
    (2, 2): "southeast",
}

CUTOFF = 100


def l1(start, goal):
    sr, sc = start
    gr, gc = goal
    return abs(gr - sr) + abs(gc - sc)


def adjacentPos(pos):
    r, c = pos
    return [(r - 1, c), (r, c - 1), (r + 1, c), (r, c + 1)]


def which_part(start, end, x):
    if not (start <= x <= end):
        raise ValueError(f"x is not in the range [{start}, {end}]")

    n = end - start + 1
    base = n // 3
    remainder = n % 3

    if remainder == 0:
        L1 = L2 = base
    elif remainder == 1:
        L1 = base
        L2 = base + 1
    else:  # remainder == 2
        L1 = base + 1
        L2 = base

    b1_end = start + L1 - 1
    b2_end = b1_end + L2

    if x <= b1_end:
        return 0
    elif x <= b2_end:
        return 1
    else:
        return 2


def get_center_bounds(tiles):
    min_map_x = np.min(tiles[:, 0])
    min_map_y = np.min(tiles[:, 1])
    max_map_x = np.max(tiles[:, 0])
    max_map_y = np.max(tiles[:, 1])

    n = max_map_x - min_map_x + 1
    base = n // 3
    remainder = n % 3

    if remainder == 0:
        L1 = L2 = base
    elif remainder == 1:
        L1 = base
        L2 = base + 1
    else:  # remainder == 2
        L1 = base + 1
        L2 = base

    b1_end_x = min_map_x + L1 - 1
    b2_end_x = b1_end_x + L2

    n = max_map_y - min_map_y + 1
    base = n // 3
    remainder = n % 3

    if remainder == 0:
        L1 = L2 = base
    elif remainder == 1:
        L1 = base
        L2 = base + 1
    else:  # remainder == 2
        L1 = base + 1
        L2 = base

    b1_end_y = min_map_y + L1 - 1
    b2_end_y = b1_end_y + L2

    return (b1_end_x + 1, b2_end_x, b1_end_y + 1, b2_end_y)


def get_bounds(tiles):
    min_r = np.min(tiles[:, 0])
    max_r = np.max(tiles[:, 0])
    min_c = np.min(tiles[:, 1])
    max_c = np.max(tiles[:, 1])
    return (min_r, max_r, min_c, max_c)


def get_area(tiles, x, y):
    min_map_x = np.min(tiles[:, 0])
    min_map_y = np.min(tiles[:, 1])
    max_map_x = np.max(tiles[:, 0])
    max_map_y = np.max(tiles[:, 1])
    x_part = which_part(min_map_x, max_map_x, x)
    y_part = which_part(min_map_y, max_map_y, y)
    return AREA_TABLE[(x_part, y_part)]


def a_star_bounded(realm_map, start, goal, bounds=None):
    """Bounded A* that returns the first direction and full path length.

    Args:
      realm_map: Map containing tiles and habitable_tiles.
      start, goal: (row, col) tuples.
      bounds: Optional (min_r, max_r, min_c, max_c) inclusive search window.
        If provided, the search is restricted to this rectangle; otherwise the
        entire map interior is searched.
    Returns:
      (direction, path_length): direction is a (dr, dc) step from start toward
      goal, or (0, 0) if no path exists. path_length is the number of steps in
      the shortest path, or inf when no path is found.
    """
    tiles = realm_map.tiles
    habitable = realm_map.habitable_tiles
    bounds_key = tuple(bounds) if bounds is not None else None

    # cache_key = ("bounded", start, goal, bounds_key)
    # if cache_key in realm_map.pathfinding_cache:
    #     return realm_map.pathfinding_cache[cache_key]

    def in_search_area(pos):
        r, c = pos
        if bounds_key is not None:
            min_r, max_r, min_c, max_c = bounds_key
            if r < min_r or r > max_r or c < min_c or c > max_c:
                return False
        return in_bounds(r, c, tiles.shape) and habitable[r, c] != 0

    if start == goal and in_search_area(start):
        # realm_map.pathfinding_cache[cache_key] = ((0, 0), 0)
        return ((0, 0), 0)
    if not in_search_area(start) or not in_search_area(goal):
        # realm_map.pathfinding_cache[cache_key] = ((0, 0), float("inf"))
        return ((0, 0), float("inf"))

    pq = [(l1(start, goal), 0, start)]  # (priority, cost_so_far, position)
    backtrace = {}
    cost = {start: 0}
    found = False

    while pq:
        _, cur_cost, cur = heapq.heappop(pq)
        if cur == goal:
            found = True
            break

        for nxt in adjacentPos(cur):
            if not in_search_area(nxt):
                continue

            newCost = cur_cost + 1
            if nxt not in cost or newCost < cost[nxt]:
                cost[nxt] = newCost
                priority = newCost + l1(goal, nxt)
                heapq.heappush(pq, (priority, newCost, nxt))
                backtrace[nxt] = cur

    if not found:
        # realm_map.pathfinding_cache[cache_key] = ((0, 0), float("inf"))
        return ((0, 0), float("inf"))

    cur = goal
    while backtrace.get(cur) and backtrace[cur] != start:
        cur = backtrace[cur]

    sr, sc = start
    gr, gc = cur
    direction = (gr - sr, gc - sc)
    path_length = cost[goal]
    # realm_map.pathfinding_cache[cache_key] = (direction, path_length)
    return (direction, path_length)
