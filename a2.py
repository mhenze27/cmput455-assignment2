# CMPUT 455 Assignment 2 starter code
# This is a sample solution for assignment 1.
# Implement the new commands to complete the assignment
# Full assignment specification and game rules on Canvas

import ast
import sys
import random
import time
from sys import stderr
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Assignment restrictions (see assignment page)
# ---------------------------------------------------------------------------
MIN_HEAPS = 1
MAX_HEAPS = 20
MIN_TOKENS = 1
MAX_TOKENS = 20
MIN_VALUE = 1
MAX_VALUE = 20
KOMI_LIMIT = 100  # -100 < komi < 100, and komi must be an integer + 0.5

# The time limit, in seconds, for a single solve or genmove command
MIN_TIMELIMIT = 1
MAX_TIMELIMIT = 100
DEFAULT_TIMELIMIT = 1

# Sets a cap for items in the tt
MAX_TT_SIZE = 1E9

BLACK = 'b'
WHITE = 'w'
COLORS = (BLACK, WHITE)

Token = Tuple[str, int]
Heap = List[Token]
Heaps = List[Heap]


def not_yet() -> bool:
    raise NotImplementedError("Command not implemented.")
    return False


def print_error(error: str) -> None:
    print(error, file=stderr)


def opponent(color: str) -> str:
    return WHITE if color == BLACK else BLACK


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def is_int(obj: Any) -> bool:
    # bool is a subclass of int; True/False are not valid values
    return isinstance(obj, int) and not isinstance(obj, bool)


def is_token(obj: Any) -> bool:
    return (isinstance(obj, tuple)
            and len(obj) == 2
            and obj[0] in COLORS
            and is_int(obj[1])
            and MIN_VALUE <= obj[1] <= MAX_VALUE)


def is_heap(obj: Any) -> bool:
    return (isinstance(obj, list)
            and MIN_TOKENS <= len(obj) <= MAX_TOKENS
            and all(is_token(token) for token in obj))


def is_heaps(obj: Any) -> bool:
    return (isinstance(obj, list)
            and MIN_HEAPS <= len(obj) <= MAX_HEAPS
            and all(is_heap(heap) for heap in obj))


def parse_komi(text: str) -> Optional[float]:
    try:
        komi = float(text)
    except ValueError:
        return None
    if not (-KOMI_LIMIT < komi < KOMI_LIMIT):
        return None
    if (komi - 0.5) != int(komi - 0.5):
        return None
    return komi


def parse_heaps(text: str) -> Optional[Heaps]:
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None
    if not is_heaps(parsed):
        return None
    return parsed


def parse_heap_number(args: str) -> Optional[int]:
    parts = args.split()
    if len(parts) != 1:
        return None
    try:
        return int(parts[0])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class HeapGo:
    def __init__(self, komi: float, heaps: Heaps) -> None:
        self.komi = komi
        self.heaps = heaps
        self.toplay = BLACK
        self.score = {BLACK: 0, WHITE: komi}

        self.history = [] # A stack to store the history of game states

    def __str__(self) -> str:
        return "k {} {}".format(self.komi, self.heaps)

    def is_legal(self, heap_number: int) -> bool:
        return 0 <= heap_number < len(self.heaps) and len(self.heaps[heap_number]) > 0

    # Like is_legal but assuming the heap number is already in range
    # def is_valid(self, heap_number: int) -> bool:
    #     return len(self.heaps[heap_number]) > 0

    def legal_moves(self) -> List[int]:
        legal_moves = [i for i in range(len(self.heaps)) if len(self.heaps[i]) > 0]
        return legal_moves

    def game_over(self, legal_moves=None) -> bool:
        if legal_moves is None:
            return len(self.legal_moves()) == 0
        return len(legal_moves) == 0

    def play(self, heap_number: int) -> bool:
        # Check if move is legal
        if not self.is_legal(heap_number):
            return False

        # print(f"history: {self.history}")

        # Save the current board state
        current_board = [heap.copy() for heap in self.heaps]
        current_score = self.score.copy()
        current_player = self.toplay
        stored_state = (current_board, current_score, current_player)
        self.history.append(stored_state)

        # print(f"history: {self.history}")

        # Play the move
        heap = self.heaps[heap_number]
        gained = 0
        # Rule 1: take all own-color tokens from the top
        while heap and heap[-1][0] == self.toplay:
            gained += heap.pop()[1]
        # Rule 2: then one opponent token, if any remain
        if heap:
            gained += heap.pop()[1]
        self.score[self.toplay] += gained
        self.toplay = opponent(self.toplay)

        return True

    def winner(self, legal_moves=None) -> Optional[str]:
        if legal_moves is None:
            if not self.game_over():
                return None
        else:
            if not self.game_over(legal_moves):
                return None
        if self.score[BLACK] > self.score[WHITE]:
            return BLACK
        if self.score[WHITE] > self.score[BLACK]:
            return WHITE
        return None  # draw; impossible with komi = integer + 0.5

    # Need to add undo for the solver algorithm
    def undo(self) -> bool:
        # print(f"board before undo: {self.heaps}")
        # print(f"history: {self.history}")
        # Revert the board to the previous state
        # Make sure the previous state is saved
        if len(self.history) == 0:
            print_error("CANNOT UNDO")
            return False

        # Load the most recent version of the state from the history stack
        restored_state = self.history.pop(-1)

        self.heaps = restored_state[0]
        self.score = restored_state[1]
        self.toplay = restored_state[2]

        # print(f"board after undo: {self.heaps}")
        # print(f"history: {self.history}")

        return True

    def get_state_code(self):
        # Calculates the code for the state for the transposition table
        # 3 important things score, player, heaps
        # tuple of tokens left per heap
        if self.toplay == BLACK:
            code = f"{self.score[BLACK]-self.score[WHITE]}, {tuple(len(x) for x in self.heaps)}"
        else:
            code = f"{self.score[WHITE]-self.score[BLACK]}, {tuple(-len(x) for x in self.heaps)}"
        return code


CommandMap = Dict[str, Callable[[str], bool]]


class CommandInterface:
    def __init__(self) -> None:
        self.game: Optional[HeapGo] = None
        self.timelimit = DEFAULT_TIMELIMIT
        # you can add your own initialisation here
        self.commands: CommandMap = {
            "help": self.cmd_help,
            "heapgo": self.cmd_heapgo,
            "show": self.cmd_show,
            "toplay": self.cmd_toplay,
            "play": self.cmd_play,
            "legal": self.cmd_legal,
            "genmove": self.cmd_genmove,
            "score": self.cmd_score,
            "winner": self.cmd_winner,
            "solve": self.cmd_solve,
            "timelimit": self.cmd_timelimit,
            "undo": self.cmd_undo, # For testing
            "feedback": self.cmd_enable_feedback,
            }

        self.start_time = -1# Keep track of the start time for the timelimit clock
        self.deadline = -1
        self.out_of_time = False
        self.out_of_time_printed = False

        self.node_count = 0 # keep track of the number of nodes visited
        self.max_depth = 0
        self.second_counter = 0

        self.initial_history_count = 0

        self.feedback = False

        self.transposition_table = {}

#============================================================================
# Command implementations
#============================================================================
    def cmd_heapgo(self, args: str) -> bool:
        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            print_error("usage: heapgo komi game")
            return False
        komi = parse_komi(parts[0])
        if komi is None:
            print_error("invalid komi: {}".format(parts[0]))
            return False
        heaps = parse_heaps(parts[1])
        if heaps is None:
            print_error("invalid game: {}".format(parts[1]))
            return False
        self.game = HeapGo(komi, heaps)
        return True

    def cmd_show(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        print(self.game)
        return True

    def cmd_toplay(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        if args not in COLORS:
            print_error("invalid color: {}".format(args))
            return False
        self.game.toplay = args
        return True

    # Plays a move
    def cmd_play(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        heap_number = parse_heap_number(args)
        if heap_number is None:
            print_error("invalid heap number: {}".format(args))
            return False
        if not self.game.play(heap_number):
            print_error("illegal move: {}".format(heap_number))
            return False
        return True

    def cmd_legal(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        heap_number = parse_heap_number(args)
        if heap_number is None:
            print_error("invalid heap number: {}".format(args))
            return False
        print("yes" if self.game.is_legal(heap_number) else "no")
        return True

    def cmd_genmove(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        
        # Reset the TT
        self.reset_transposition_table()

        legal_moves = self.game.legal_moves()
        if not legal_moves:
            print_error("no legal moves")
            return False
        # Try to play a winning move if one exists and can be found in time
        self.start_clock()
        winning_move = self.get_winning_move(self.game)

        # Check if we found a winning move
        if not self.check_time() or winning_move is None or winning_move is False:
            # Play a random move
            move = random.choice(legal_moves)
            self.game.play(move)
            print(move)
            return True

        # If we found a winning move play it
        self.game.play(winning_move)
        print(winning_move)

        return True

    def cmd_score(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        print("b {} w {}".format(self.game.score[BLACK], self.game.score[WHITE]))
        return True

    def cmd_winner(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        winner = self.game.winner()
        if winner is None:
            print_error("game not over" if not self.game.game_over() else "draw")
            return False
        print(winner)
        return True

    def cmd_undo(self, args):
        return self.game.undo()

#============================================================================
# You need to implement the following methods.
#============================================================================
    def cmd_solve(self, args: str) -> bool:
        # Start the timer
        self.start_clock()

        # Make sure a game exists
        if self.game is None:
            if self.feedback:
                print_error("no game started")
            return False

        # Reset the transposition table to empty
        self.reset_transposition_table()

        self.node_count = 0
        self.max_depth = 0
        self.initial_history_count = len(self.game.history)
        self.second_counter = 0
        
        # Minimax OR is current player, AND is other player
        #root_player = self.game.toplay
        opponent_player = opponent(self.game.toplay)

        winning_move = self.get_winning_move(self.game)
        if not self.check_time():
            if self.feedback:
                print_error(f"Status: Elapsed time: {self.get_elapsed_time():.4f}. Nodes explored: {self.node_count}. TT Size: {len(self.transposition_table.keys())}. TT Memory: {self.get_tt_memory():f}MB. Depth: {len(self.game.history)-self.initial_history_count}. Max depth: {self.max_depth}.")
            return False
        
        # The current player will win
        if winning_move is not None:
            if self.feedback:
                print_error("\nSolution found!")
                print_error("Root player will win.")
            print(f"{self.game.toplay} {winning_move}")
            if self.feedback:
                print_error(f"Status: Elapsed time: {self.get_elapsed_time():.4f}. Nodes explored: {self.node_count}. TT Size: {len(self.transposition_table.keys())}. TT Memory: {self.get_tt_memory():f}MB. Depth: {len(self.game.history)-self.initial_history_count}. Max depth: {self.max_depth}.")
            return True

        # The opponent player can win
        if self.feedback:
            print_error("\nSolution found!")
            print_error("Opponent player will win.")
        print(opponent_player)
        if self.feedback:
            print_error(f"Status: Elapsed time: {self.get_elapsed_time():.4f}. Nodes explored: {self.node_count}. TT Size: {len(self.transposition_table.keys())}. TT Memory: {self.get_tt_memory():f}MB. Depth: {len(self.game.history)-self.initial_history_count}. Max depth: {self.max_depth}.")
        return True

    def get_winning_move(self, game: HeapGo):
        # Return a winning move
        if not self.check_time() or self.out_of_time:
            if self.feedback and not self.out_of_time_printed:
                print_error("OUT OF TIME.")
                self.out_of_time_printed = True
            return False

        legal_moves = game.legal_moves()
        for move in legal_moves:
            game.play(move)
            is_winning = not self.negamax(game)
            game.undo()
            if not self.check_time() or self.out_of_time:
                if self.feedback and not self.out_of_time_printed:
                    print_error("OUT OF TIME.")
                    self.out_of_time_printed = True
                return False
            # Print status after each root level node
            if self.feedback:
                print_error(f"\nStatus: Move {move} of {len(legal_moves)}. Result: {'success' if is_winning else 'not successful'}. Nodes explored: {self.node_count}. TT Size: {len(self.transposition_table.keys())}. Elapsed time: {self.get_elapsed_time():.2f}.\n")
            if is_winning:
                return move

        return None

    def negamax(self, game: HeapGo):
        self.node_count += 1
        if self.feedback:
            if (len(self.game.history) - self.initial_history_count) > self.max_depth:
                self.max_depth = len(self.game.history) - self.initial_history_count
            if self.node_count % 1000 == 0 and int(self.get_elapsed_time()) >= self.second_counter:
                self.second_counter += 1
                if self.feedback:
                    print_error(f"Status: Elapsed time: {int(self.get_elapsed_time())}. Nodes explored: {self.node_count}. TT Size: {len(self.transposition_table.keys())}. Depth: {len(self.game.history)-self.initial_history_count}. Max depth: {self.max_depth}.")

        if not self.check_time() or self.out_of_time:
            if self.feedback and not self.out_of_time_printed:   
                print_error("OUT OF TIME.")
                self.out_of_time_printed = True
            return False

        # Get a list of legal moves
        legal_moves = game.legal_moves()

        # We only need to check this on terminal nodes
        if len(legal_moves) == 0:
            # Who is the player
            # toplay is the player
            # Check if game is already over
            if game.winner(legal_moves) == game.toplay:
                # Game is already won
                return True
            else:
                # Game is won by opponent
                return False

        # Go through all legal moves
        for move in legal_moves:
            game.play(move)

            # Check if the result is in the transposition table
            state_code = game.get_state_code()
            result = self.transposition_table.get(state_code)
            if result is None:
                is_winning_move = not self.negamax(game)
                # Only store in the tt if the time has not run out
                # Only store in the tt if we are below the cap
                if not self.out_of_time and len(self.transposition_table) < MAX_TT_SIZE:
                    self.transposition_table[state_code] = is_winning_move
            else:
                is_winning_move = result

            #is_winning_move = not self.negamax(game)
            game.undo()
            if not self.check_time() or self.out_of_time:
                if self.feedback and not self.out_of_time_printed:   
                    print_error("OUT OF TIME.")
                    self.out_of_time_printed = True
                return False
            if is_winning_move:
                return True

        return False

    def cmd_timelimit(self, args: str) -> bool:
        """Sets the timelimit as long as the input is valid."""
        # Make sure the argument is not empty
        if len(args) == 0:
            return False
        
        input_timelimit = float(args)

        # Make sure timelimit is an integer
        if input_timelimit % 1 != 0:
            if self.feedback:
                print_error("Invalid timelimit.")
            return False

        input_timelimit = int(input_timelimit)

        # Make sure timelimit is valid
        if input_timelimit < MIN_TIMELIMIT or input_timelimit > MAX_TIMELIMIT:
            if self.feedback:
                print_error("Invalid timelimit.")
            return False

        self.timelimit = input_timelimit

        return True

    def check_time(self):
        """Check if we are over the timelimit."""
        # If the clock was never started
        if self.start_time == -1 or self.deadline == -1:
            return False 
        # If we have already determined to be out of time
        if self.out_of_time:
            return False
        
        current_time = time.perf_counter()
        if current_time > self.deadline:
            self.out_of_time = True
            return False
        return True

    def start_clock(self):
        self.start_time = time.perf_counter()
        self.deadline = self.start_time + self.timelimit
        self.out_of_time = False
        self.out_of_time_printed = False
        return True

    def get_elapsed_time(self):
        current_time = time.perf_counter()
        elapsed_time = current_time - self.start_time
        return elapsed_time

    def cmd_enable_feedback(self, args):
        print_error("Feedback enabled.")
        self.feedback = True
        return True

    def reset_transposition_table(self):
        self.transposition_table = {}
        return True

    def get_tt_memory(self):
        # Get the size of the dictionary
        dict_size = sys.getsizeof(self.transposition_table)
        # Get the size of all the items
        items_size = 0
        for key, value in self.transposition_table.items():
            items_size += sys.getsizeof(key)
        total_size = dict_size + items_size
        # Convert the size to MB
        total_size_mb = total_size / 2**20
        return total_size_mb

#============================================================================
# End of functions requiring implementation
#============================================================================

#============================================================================
# The code below should not need modification
# Anyway, you may change or add to this code as you see fit
#============================================================================
    def cmd_help(self, ignore_args: str) -> bool:
        print("\nKnown commands:")
        for cmd in self.commands:
            print(cmd)
        return True

    def process_command(self, cmd_name: str, cmd_args: str) -> None:
        status = "= -1"
        cmd = self.commands.get(cmd_name)
        if cmd:
            try:
                if cmd(cmd_args):
                    status = "= 1"
            except Exception as e:
                print_error(f"Command {cmd_name} with arguments {cmd_args} failed with exception: {e}")
        else:
            print_error("Unknown command. Type 'help' for commands.")
        print(status)

    def main_loop(self) -> None:
        process_commands = True
        while process_commands:
            try:
                line = input()
            except EOFError:
                break
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            cmd_name = parts[0]
            if cmd_name == "exit":
                process_commands = False
                continue
            cmd_args = parts[1] if len(parts) > 1 else ""
            self.process_command(cmd_name, cmd_args)


if __name__ == "__main__":
    interface = CommandInterface()
    interface.main_loop()
