"""Real walking distance to the checkpoints.

The spec suggests the Manhattan distance |dx| + |dy|. On a board with walls and holes it can lie:
a robot can be 1 cell from a checkpoint in Manhattan distance but have to walk around a wall.
So we compute, once per board, a breadth-first search (BFS) from each checkpoint:
dist[cp][y][x] = number of steps to reach checkpoint cp from (x, y) without crossing a wall or a hole.
"""
from collections import deque
from typing import Dict, List

from ..model import Board, Direction, Position

UNREACHABLE = 99


class DistanceMap:
    def __init__(self, board: Board):
        self.board = board
        self.dist: Dict[int, List[List[int]]] = {n: self._bfs(pos) for n, pos in board.checkpoints.items()}
        # length of the path from checkpoint n to checkpoint n+1
        self.leg = {n: self.distance(board.checkpoints[n], n + 1) for n in (1, 2)}

    def _bfs(self, start: Position) -> List[List[int]]:
        size = self.board.SIZE
        dist = [[UNREACHABLE] * size for _ in range(size)]
        dist[start.y][start.x] = 0
        queue = deque([start])
        while queue:
            pos = queue.popleft()
            for direction in Direction:
                nxt = pos.step(direction)
                if not self.board.in_bounds(nxt) or dist[nxt.y][nxt.x] != UNREACHABLE:
                    continue
                tile = self.board.tile_at(nxt)
                if tile.blocks() or tile.is_hole():
                    continue
                dist[nxt.y][nxt.x] = dist[pos.y][pos.x] + 1
                queue.append(nxt)
        return dist

    def distance(self, pos: Position, checkpoint: int) -> int:
        if not self.board.in_bounds(pos):
            return UNREACHABLE
        return self.dist[checkpoint][pos.y][pos.x]

    def remaining(self, pos: Position, next_cp: int) -> int:
        """Cells left in the whole race: to the next checkpoint, then from checkpoint to checkpoint."""
        if next_cp > 3:
            return 0
        return self.distance(pos, next_cp) + sum(self.leg[n] for n in range(next_cp, 3))
