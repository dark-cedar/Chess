from __future__ import annotations
import copy


def sign(number: int) -> int:
    if number > 0:
        return 1
    elif number < 0:
        return -1
    else:
        return 0


class State: pass


class Cell:
    def __init__(self, x, y) -> None:
        if not 1 <= x <= 8 or not 1 <= y <= 8:
            raise ValueError("Cell must lie within the chess board.")
        self.x, self.y = x, y

    def __iter__(self):  # so, now you can tuple(Cell(x, y)) == (x, y)
        yield self.x
        yield self.y

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.x}, {self.y})"
    
    def __eq__(self, other: Cell) -> bool:
        return self.x == other.x and self.y == other.y
    
    @classmethod
    def from_abbreviation(cls, abbreviation: str) -> Cell:
        if len(abbreviation) != 2:
            raise ValueError("Incorrect abbreviation.")
        return cls(ord(abbreviation[0]) - ord('a') + 1, int(abbreviation[1]))


class Move:
    def __init__(self, cell_from: Cell, cell_to: Cell) -> None:
        self.cell_from: Cell = cell_from
        self.cell_to: Cell = cell_to

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.cell_from}, {self.cell_to})"
    
   
class EnumeratedMove(Move):
    def __init__(self, cell_from: Cell, cell_to: Cell, move_number: int = 1) -> None:
        super().__init__(cell_from, cell_to)
        self.move_number: int = move_number

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.cell_from}, {self.cell_to}, {self.move_number})"


# ----------------------- Definition of Figures
class Figure:
    """
    1   - white
    -1  - black
    """

    basic_letter: str = 'f'

    def __init__(self, state: State, current_position: Cell, color: int) -> None:
        self._state: State = state
        self._current_position: Cell = current_position
        if color not in (-1, 1):
            raise ValueError("Color must be either 1 or -1.")
        self._color: int = color
        # moves
        self.moves: list[EnumeratedMove] = []
        self.number_of_moves: int = 0

    @property
    def color(self) -> int:
        return self._color
    
    @property
    def human_color(self) -> str:
        return "white" if self.color == 1 else "black"
    
    @property
    def letter(self) -> str:
        return self.__class__.basic_letter.capitalize() if self.color == 1 else self.__class__.basic_letter
    
    @property
    def last_move(self) -> EnumeratedMove | None:
        if self.number_of_moves > 0:
            return self.moves[self.number_of_moves - 1]
        return None

    def _add_move(self, move: EnumeratedMove) -> None:
        self.moves.append(move)
        self.number_of_moves += 1
        # to state
        self._state.moves.append(move)
        self._state.number_of_moves += 1

    def _is_cell_under_attack(self, cell: Cell) -> bool:
        return False

    def is_initial_position(self) -> bool:
        return self.number_of_moves == 0

    def _make_move(self, cell: Cell) -> None:
        "Makes move without checking correctness"
        figure_copy: Figure = copy.copy(self)
        figure_copy._current_position = cell
        figure_copy.moves = copy.copy(self.moves)
        figure_copy._add_move(EnumeratedMove(self._current_position, cell, self._state.number_of_moves + 1))
        self._state.board[cell.y - 1][cell.x - 1] = figure_copy
        self._state.board[self._current_position.y - 1][self._current_position.x - 1] = None
    
    def make_move(self, cell: Cell) -> None:
        "Checks correctness and makes move"
        raise ValueError("Pure figure cannot make any moves.")
    
    def _make_move_on_copied(self, cell: Cell) -> State:
        state_copy: State = self._state.get_copy()
        state_copy._make_move(Move(self._current_position, cell))
        return state_copy

    def make_move_on_copied(self, cell: Cell) -> State:
        state_copy: State = self._state.get_copy()
        state_copy.make_move(Move(self._current_position, cell))
        return state_copy

    def get_possible_moves(self) -> list[Cell]:
        result = []
        for y in range(1, 9):
            for x in range(1, 9):
                state_copy: State = self._state.get_copy()
                try:
                    state_copy.make_move(Move(self._current_position, Cell(x, y)))
                    result.append(Cell(x, y))
                except:
                    continue
        return result

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._current_position}, {self.human_color})"


class King(Figure):
    basic_letter: str = 'k'

    def __init__(self, *args, **kwargs) -> None:
        return super().__init__(*args, **kwargs)
    
    def _is_cell_under_attack(self, cell: Cell) -> bool:
        if self._current_position == cell:
            return False
        return abs(self._current_position.x - cell.x) <= 1 and abs(self._current_position.y - cell.y) <= 1

    def make_move(self, cell: Cell) -> None:
        """
        Problems:
        1) Castling
        """
        # castling:
        figure: Figure | None = copy.copy(self._state.get_by_cell(cell))
        if figure is not None and isinstance(figure, Rook) and figure.is_initial_position() and self.is_initial_position():
            # checking that all cells between are empty
            x_from = min(self._current_position.x, cell.x)
            x_to = max(self._current_position.x, cell.x)
            for x in range(x_from + 1, x_to):
                if self._state.get_by_cell(Cell(x, cell.y)) is not None:
                    raise ValueError("You cannot make castling while there are figures between your rook and king.")
            if self._state._is_king_in_check(self.color):
                raise ValueError("Your king in check, you cannot make castling")
            rook_new_position: Cell = Cell(self._current_position.x + sign(cell.x - self._current_position.x), cell.y)
            king_new_position: Cell = Cell(self._current_position.x + 2 * sign(cell.x - self._current_position.x), cell.y)
            # checking rook new position on being under attack
            if self._state._is_cell_under_attack(rook_new_position, self.color * -1):
                raise ValueError("Cell on king's path in under attack, you cannot make castling in this situation.")
            # checking on being in check on copied state
            state_copy = self._make_move_on_copied(king_new_position)
            state_copy.change_king_position_by_color(king_new_position, self.color)
            state_copy.board[rook_new_position.y - 1][rook_new_position.x - 1] = state_copy.board[figure._current_position.y - 1][figure._current_position.x - 1]
            state_copy.board[rook_new_position.y - 1][rook_new_position.x - 1]._current_position = rook_new_position
            state_copy.board[figure._current_position.y - 1][figure._current_position.x - 1] = None
            if state_copy._is_king_in_check(self.color):
                raise ValueError("You will be in check, you cannot make such move.")
            # all tests passed
            self._make_move(king_new_position)
            self._state.change_king_position_by_color(king_new_position, self.color)
            self._state.board[rook_new_position.y - 1][rook_new_position.x - 1] = self._state.board[figure._current_position.y - 1][figure._current_position.x - 1]
            self._state.board[rook_new_position.y - 1][rook_new_position.x - 1]._current_position = rook_new_position
            self._state.board[figure._current_position.y - 1][figure._current_position.x - 1] = None
            return
        # if not castling:
        if not self._is_cell_under_attack(cell):
            raise ValueError("Kings don't move like that.")
        if figure is not None and figure.color == self.color:
            raise ValueError("You cannot beat your own figure.")
        state_copy = self._make_move_on_copied(cell)
        state_copy.change_king_position_by_color(cell, self.color)
        if state_copy._is_king_in_check(self.color):
            raise ValueError("You will be in check, you cannot make such move.")
        # all tests passed
        self._make_move(cell)
        self._state.change_king_position_by_color(cell, self.color)


class Queen(Figure):
    basic_letter: str = 'q'

    def __init__(self, *args, **kwargs) -> None:
        return super().__init__(*args, **kwargs)
    
    def _is_cell_under_attack(self, cell: Cell) -> bool:
        if self._current_position == cell:
            return False
        # as bishop
        if abs(self._current_position.x - cell.x) == abs(self._current_position.y - cell.y):
            # checking all cells between
            vector: tuple[int, int] = (sign(cell.x - self._current_position.x), sign(cell.y - self._current_position.y))
            x, y = self._current_position.x, self._current_position.y
            while True:
                x += vector[0]
                y += vector[1]
                if Cell(x, y) == cell:
                    break
                if self._state.get_by_cell(Cell(x, y)) is not None:
                    return False
            return True
        # as rook
        # vertically
        if self._current_position.x == cell.x:
            # checking all cells between
            y_from = min(self._current_position.y, cell.y)
            y_to = max(self._current_position.y, cell.y)
            for y in range(y_from + 1, y_to):
                if self._state.get_by_cell(Cell(cell.x, y)) is not None:
                    return False
            return True
        # horizontally
        if self._current_position.y == cell.y:
            x_from = min(self._current_position.x, cell.x)
            x_to = max(self._current_position.x, cell.x)
            for x in range(x_from + 1, x_to):
                if self._state.get_by_cell(Cell(x, cell.y)) is not None:
                    return False
            return True
        return False

    def make_move(self, cell: Cell) -> None:
        if not self._is_cell_under_attack(cell):
            raise ValueError("Queens don't move like that.")
        state_copy = self._make_move_on_copied(cell)
        if state_copy._is_king_in_check(self.color):
            raise ValueError("You will be in check, you cannot make such move.")
        # all tests passed
        self._make_move(cell)


class Bishop(Figure):
    basic_letter: str = 'b'

    def __init__(self, *args, **kwargs) -> None:
        return super().__init__(*args, **kwargs)
    
    def _is_cell_under_attack(self, cell: Cell) -> bool:
        if self._current_position == cell:
            return False
        if not abs(self._current_position.x - cell.x) == abs(self._current_position.y - cell.y):
            return False
        # checking all cells between
        vector: tuple[int, int] = (sign(cell.x - self._current_position.x), sign(cell.y - self._current_position.y))
        x, y = self._current_position.x, self._current_position.y
        while True:
            x += vector[0]
            y += vector[1]
            if Cell(x, y) == cell:
                break
            if self._state.get_by_cell(Cell(x, y)) is not None:
                return False
        return True

    def make_move(self, cell: Cell) -> None:
        if not self._is_cell_under_attack(cell):
            raise ValueError("Bishops don't move like that.")
        state_copy = self._make_move_on_copied(cell)
        if state_copy._is_king_in_check(self.color):
            raise ValueError("You will be in check, you cannot make such move.")
        # all tests passed
        self._make_move(cell)


class Knight(Figure):
    basic_letter: str = 'h'

    def __init__(self, *args, **kwargs) -> None:
        return super().__init__(*args, **kwargs)
    
    def _is_cell_under_attack(self, cell: Cell) -> bool:
        return sorted([abs(self._current_position.x - cell.x), abs(self._current_position.y - cell.y)]) == [1, 2]

    def make_move(self, cell: Cell) -> None:
        if not self._is_cell_under_attack(cell):
            raise ValueError("Knights don't move like that.")
        state_copy = self._make_move_on_copied(cell)
        if state_copy._is_king_in_check(self.color):
            raise ValueError("You will be in check, you cannot make such move.")
        # all tests passed
        self._make_move(cell)

    def get_possible_moves(self) -> list[Cell]:
        result = []
        x, y = tuple(self._current_position)
        possible_unchecked: list[tuple[int, int]] = [
            (x - 1, y + 2), (x - 1, y - 2), (x + 1, y + 2), (x + 1, y - 2),
            (x + 2, y - 1), (x - 2, y - 1), (x + 2, y + 1), (x - 2, y + 1),
        ]
        for x, y in possible_unchecked:
            state_copy: State = self._state.get_copy()
            try:
                state_copy.make_move(Move(self._current_position, Cell(x, y)))
                result.append(Cell(x, y))
            except:
                continue
        return result


class Rook(Figure):
    basic_letter: str = 'r'

    def __init__(self, *args, **kwargs) -> None:
        return super().__init__(*args, **kwargs)
    
    def _is_cell_under_attack(self, cell: Cell) -> bool:
        if self._current_position == cell:
            return False
        # vertically
        if self._current_position.x == cell.x:
            # checking all cells between
            y_from = min(self._current_position.y, cell.y)
            y_to = max(self._current_position.y, cell.y)
            for y in range(y_from + 1, y_to):
                if self._state.get_by_cell(Cell(cell.x, y)) is not None:
                    return False
            return True
        # horizontally
        if self._current_position.y == cell.y:
            x_from = min(self._current_position.x, cell.x)
            x_to = max(self._current_position.x, cell.x)
            for x in range(x_from + 1, x_to):
                if self._state.get_by_cell(Cell(x, cell.y)) is not None:
                    return False
            return True
        return False

    def make_move(self, cell: Cell) -> None:
        if not self._is_cell_under_attack(cell):
            raise ValueError("Rooks don't move like that.")
        state_copy = self._make_move_on_copied(cell)
        if state_copy._is_king_in_check(self.color):
            raise ValueError("You will be in check, you cannot make such move.")
        # all tests passed
        self._make_move(cell)


class Pawn(Figure):
    basic_letter: str = 'p'

    def __init__(self, *args, **kwargs) -> None:
        return super().__init__(*args, **kwargs)

    def _is_cell_under_attack(self, cell: Cell) -> bool:
        return abs(self._current_position.x - cell.x) == 1 and self._current_position.y == cell.y + self.color
    
    def transform_to_queen(self, cell: Cell) -> None:
        pawn: Pawn = self._state.get_by_cell(cell)
        queen: Queen = Queen(pawn._state, pawn._current_position, pawn.color)
        queen.moves = pawn.moves
        queen.number_of_moves = pawn.number_of_moves
        # changing
        pawn._state.board[pawn._current_position.y - 1][pawn._current_position.x - 1] = queen

    def make_move(self, cell: Cell) -> None:
        # 1 (just vertically one or two steps)
        if self._current_position.x == cell.x and (self._current_position.y + self.color == cell.y or (self.is_initial_position() and self._current_position.y + 2 * self.color == cell.y)):
            """
            Problems:
            1) maybe field is already occupied
            2) maybe in check already
            3) maybe will be in check
            4) we can be transformed to queen
            """
            is_transformation: bool = (cell.y == 8 and self.color == 1) or (cell.y == 1 and self.color == -1)
            # 1)
            if self._state.get_by_cell(cell) is not None:
                raise ValueError("This field is already occupied.")
            # 2), 3)
            # we can move only if we will protect the king from being in check
            state_copy = self._make_move_on_copied(cell)
            if is_transformation:
                state_copy.get_by_cell(cell).transform_to_queen(cell)
            if state_copy._is_king_in_check(self.color):
                raise ValueError("You will be in check, you cannot make such move.")
            # all tests passed
            self._make_move(cell)
            if is_transformation:
                self.transform_to_queen(cell)
            return
        # 2 (we beat somebody)
        if abs(self._current_position.x - cell.x) == 1 and self._current_position.y + self.color == cell.y:
            """
            Problems:
            1) That interesting move "En passant"
            """
            figure: Figure | None = self._state.get_by_cell(cell)
            if figure is not None:  # somebody is on this cell
                if figure.color == self.color:
                    raise ValueError("You cannot beat your own figures.")
                is_transformation: bool = (cell.y == 8 and self.color == 1) or (cell.y == 1 and self.color == -1)
                state_copy = self._make_move_on_copied(cell)
                if is_transformation:
                    state_copy.get_by_cell(cell).transform_to_queen(cell)
                if state_copy._is_king_in_check(self.color):
                    raise ValueError("You will be in check, you cannot make such move.")
                # all tests passed
                self._make_move(cell)
                if is_transformation:
                    self.transform_to_queen(cell)
                return
            else:  # nobody is on this cell (En passant situation)
                figure: Figure | None = self._state.get_by_cell(Cell(cell.x, self._current_position.y))
                if figure is None or figure.color == self.color or not isinstance(figure, Pawn) or not figure.number_of_moves == 1 or not self._state.number_of_moves == figure.last_move.move_number:
                    raise ValueError("You cannot make such move, it's not En passant situation.")
                state_copy = self._make_move_on_copied(cell)
                state_copy.board[figure._current_position.y - 1][figure._current_position.x - 1] = None
                if state_copy._is_king_in_check(self.color):
                    raise ValueError("You will be in check, you cannot make such move.")
                # all tests passed
                self._make_move(cell)
                self._state.board[figure._current_position.y - 1][figure._current_position.x - 1] = None
                return
        raise ValueError("Pawns don't move like that.")

    def get_possible_moves(self) -> list[Cell]:
        result = []
        x, y = tuple(self._current_position)
        possible_unchecked: list[tuple[int, int]] = [
            (x, y + self.color),
            (x - 1, y + self.color),
            (x + 1, y + self.color),
        ]
        for x, y in possible_unchecked:
            state_copy: State = self._state.get_copy()
            try:
                state_copy.make_move(Move(self._current_position, Cell(x, y)))
                result.append(Cell(x, y))
            except:
                continue
        return result


LETTER_TO_FIGURE = {
    'k': King,
    'q': Queen,
    'b': Bishop,
    'h': Knight,
    'r': Rook,
    'p': Pawn,
}

COLORS = {
    1: "white",
    -1: "black",
}


def _get_figure_by_letter(state_instance: State, current_position: Cell, letter: str) -> Figure:
    figure = LETTER_TO_FIGURE[letter.lower()]
    return figure(state_instance, current_position, 1 if letter.isupper() else -1)


class State:
    """
    Main class that implements game logic

    1   - win of white
    0   - stalemate
    -1  - win of black
    """

    initial_position: str = (
        "rhbqkbhr\n"
        "pppppppp\n"
        "........\n"
        "........\n"
        "........\n"
        "........\n"
        "PPPPPPPP\n"
        "RHBQKBHR\n"
    )

    # ----------------------- public methods
    def __init__(self) -> None:
        # winning side fields
        self.is_game_over: bool = False
        self.winning_side: int = 0
        # king's positions
        self._white_king_position: Cell = Cell(5, 1)
        self._black_king_position: Cell = Cell(5, 8)
        # board fields
        self.board: list[list[Figure | None]] = self.board_from_text(self, self.__class__.initial_position)
        self.moves: list[EnumeratedMove] = []
        self.number_of_moves: int = 0
        # copy fields
        self._is_original = True

    @staticmethod
    def board_from_text(instance: State, text_board: str) -> list[list[Figure | None]]:
        text_board_as_list = list(map(lambda line: list(line), text_board.split('\n')))
        board = [[None for _ in range(8)] for _ in range(8)]
        for y in range(8):
            for x in range(8):
                if text_board_as_list[y][x] == '.':
                    continue
                board[8 - y - 1][x] = _get_figure_by_letter(instance, Cell(x + 1, 8 - y), text_board_as_list[y][x])
        return board
    
    def get_by_cell(self, cell: Cell) -> Figure | None:
        return self.board[cell.y - 1][cell.x - 1]

    @property
    def white_king(self) -> King:
        return self.get_by_cell(self._white_king_position)
    
    @property
    def black_king(self) -> King:
        return self.get_by_cell(self._black_king_position)

    def get_king_position_by_color(self, color: int) -> Cell:
        if color not in (-1, 1):
            raise ValueError("Color must be either 1 or -1.")
        if color == 1:
            return self._white_king_position
        return self._black_king_position

    def change_king_position_by_color(self, cell: Cell, color: int) -> None:
        if color not in (-1, 1):
            raise ValueError("Color must be either 1 or -1.")
        if color == 1:
            self._white_king_position = cell
        else:
            self._black_king_position = cell

    @property
    def last_move(self) -> Move | None:
        if self.number_of_moves > 0:
            return self.moves[self.number_of_moves - 1]
        return None

    @property
    def whose_move(self) -> int:  # 1 if white move else -1
        return 1 if (self.number_of_moves % 2 == 0) else -1

    def get_possible_moves(self, cell: Cell) -> list[Cell]:
        if self.is_game_over:
            return []
        figure: Figure | None = self.get_by_cell(cell)
        if figure is not None:
            return figure.get_possible_moves()
        return []
    
    def _make_move(self, move: Move) -> None:
        figure: Figure | None = self.get_by_cell(move.cell_from)
        if figure is None:
            raise ValueError("From cell has not figure on it.")
        else:
            figure._make_move(move.cell_to)

    def make_move(self, move: Move) -> None:
        figure: Figure | None = self.get_by_cell(move.cell_from)
        if figure is None:
            raise ValueError("From cell has no figure on it.")
        else:
            if figure.color != self.whose_move:
                raise ValueError(f"It's not {COLORS[figure.color]} turn.")
            figure.make_move(move.cell_to)
            if self._is_original:
                self._check_on_game_over()

    def board_to_str(self) -> str:
        lines = []
        for y in range(8, 0, -1):  # from 8 to 1
            line = ""
            for x in range(1, 9, 1):  # from 1 to 8
                figure: Figure | None = self.get_by_cell(Cell(x, y))
                if figure is None:
                    line += '.'
                else:
                    line += figure.letter
            lines.append(line)
        return '\n'.join(lines)

    def get_copy(self) -> State:
        state_copy: State = copy.copy(self)
        state_copy._is_original = False
        state_copy.board = [[None for _ in range(8)] for _ in range(8)]
        for y in range(8):
            for x in range(8):
                figure: Figure | None = self.get_by_cell(Cell(x + 1, y + 1))
                if figure is not None:
                    state_copy.board[y][x] = copy.copy(figure)
                    state_copy.board[y][x]._state = state_copy
        return state_copy
    
    def _is_cell_under_attack(self, cell: Cell, color: int):  # color - attacker color
        if color not in (-1, 1):
            raise ValueError("Color must be either 1 or -1.")
        for y in range(1, 9):
            for x in range(1, 9):
                figure: Figure | None = self.get_by_cell(Cell(x, y))
                if figure is None or figure.color != color:
                    continue
                if figure._is_cell_under_attack(cell):
                    return True
        return False

    def _is_king_in_check(self, color: int) -> bool:
        if color not in (-1, 1):
            raise ValueError("Color must be either 1 or -1.")
        king_position: Cell = self.get_king_position_by_color(color)
        return self._is_cell_under_attack(king_position, color * -1)
    
    def make_move_by_abbreviation(self, abbreviation: str) -> None:
        abbreviation_cells = abbreviation.split()
        move: Move = Move(
            Cell.from_abbreviation(abbreviation_cells[0]),
            Cell.from_abbreviation(abbreviation_cells[1]),
        )
        self.make_move(move)

    def _is_there_possible_moves_by_color(self, color: int) -> bool:
        if color not in (-1, 1):
            raise ValueError("Color must be either 1 or -1.")
        for y in range(1, 9):
            for x in range(1, 9):
                figure: Figure | None = self.get_by_cell(Cell(x, y))
                if figure is None or figure.color != color:
                    continue
                if len(figure.get_possible_moves()) != 0:
                    return True
        return False
    
    def _is_stalemate_by_color(self, color: int) -> bool:
        if color not in (-1, 1):
            raise ValueError("Color must be either 1 or -1.")
        return not self._is_there_possible_moves_by_color(color) and not self._is_king_in_check(color)

    def _is_checkmate_by_color(self, color: int) -> bool:
        if color not in (-1, 1):
            raise ValueError("Color must be either 1 or -1.")
        return not self._is_there_possible_moves_by_color(color) and self._is_king_in_check(color)
    
    def _check_on_game_over(self) -> None:
        # stalemate and checkmate checking
        possible_moves_presence: bool = self._is_there_possible_moves_by_color(self.whose_move)
        is_king_in_check: bool = self._is_king_in_check(self.whose_move)
        if not possible_moves_presence:
            self.is_game_over = True
            if is_king_in_check:
                self.winning_side = self.whose_move * -1
            else:
                self.winning_side = 0