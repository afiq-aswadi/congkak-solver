import pygame

from congkak.congkak_core import (
    BoardState,
    RuleConfig,
    apply_move,
    get_final_scores,
    get_legal_moves,
    get_winner,
    is_terminal,
)
from congkak.solver.minimax import MinimaxSolver

# colors
BG_COLOR = (245, 222, 179)  # wheat
BOARD_COLOR = (139, 90, 43)  # saddle brown
PIT_COLOR = (101, 67, 33)  # dark brown
STORE_COLOR = (85, 55, 27)  # darker brown
SEED_COLOR = (50, 50, 50)  # dark gray
HIGHLIGHT_COLOR = (255, 215, 0)  # gold
TEXT_COLOR = (255, 255, 255)
P0_COLOR = (70, 130, 180)  # steel blue
P1_COLOR = (178, 34, 34)  # firebrick

# layout constants
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 400
PIT_RADIUS = 35
STORE_WIDTH = 80
STORE_HEIGHT = 180
PIT_SPACING = 110
BOARD_MARGIN = 50


def draw_board(
    screen: pygame.Surface,
    font: pygame.font.Font,
    state: BoardState,
    legal_moves: list[int],
    selected_pit: int | None,
) -> dict[int, pygame.Rect]:
    """Draw the congkak board and return pit rects for click detection."""
    screen.fill(BG_COLOR)

    # draw board background
    board_w = WINDOW_WIDTH - 2 * BOARD_MARGIN
    board_h = WINDOW_HEIGHT - 2 * BOARD_MARGIN
    board_rect = pygame.Rect(BOARD_MARGIN, BOARD_MARGIN, board_w, board_h)
    pygame.draw.rect(screen, BOARD_COLOR, board_rect, border_radius=20)

    pit_rects: dict[int, pygame.Rect] = {}

    # calculate positions
    start_x = BOARD_MARGIN + STORE_WIDTH + 50
    row_y_top = WINDOW_HEIGHT // 2 - 50  # player 1 pits (top row)
    row_y_bottom = WINDOW_HEIGHT // 2 + 50  # player 0 pits (bottom row)

    # draw P0's store (left)
    p0_store_rect = pygame.Rect(
        BOARD_MARGIN + 20, WINDOW_HEIGHT // 2 - STORE_HEIGHT // 2, STORE_WIDTH, STORE_HEIGHT
    )
    pygame.draw.rect(screen, STORE_COLOR, p0_store_rect, border_radius=15)
    p0_store_text = font.render(str(state.pits[14]), True, TEXT_COLOR)
    screen.blit(
        p0_store_text,
        (
            p0_store_rect.centerx - p0_store_text.get_width() // 2,
            p0_store_rect.centery - p0_store_text.get_height() // 2,
        ),
    )
    # label
    label = font.render("P0", True, P0_COLOR)
    screen.blit(label, (p0_store_rect.centerx - label.get_width() // 2, p0_store_rect.bottom + 5))

    # draw P1's store (right)
    p1_store_rect = pygame.Rect(
        WINDOW_WIDTH - BOARD_MARGIN - STORE_WIDTH - 20,
        WINDOW_HEIGHT // 2 - STORE_HEIGHT // 2,
        STORE_WIDTH,
        STORE_HEIGHT,
    )
    pygame.draw.rect(screen, STORE_COLOR, p1_store_rect, border_radius=15)
    p1_store_text = font.render(str(state.pits[15]), True, TEXT_COLOR)
    screen.blit(
        p1_store_text,
        (
            p1_store_rect.centerx - p1_store_text.get_width() // 2,
            p1_store_rect.centery - p1_store_text.get_height() // 2,
        ),
    )
    label = font.render("P1", True, P1_COLOR)
    screen.blit(label, (p1_store_rect.centerx - label.get_width() // 2, p1_store_rect.bottom + 5))

    # draw pits
    for i in range(7):
        # player 0 pits (bottom row, left to right)
        x = start_x + i * PIT_SPACING
        pit_idx = i
        color = PIT_COLOR
        if pit_idx in legal_moves:
            color = HIGHLIGHT_COLOR if selected_pit == pit_idx else (140, 100, 60)

        pygame.draw.circle(screen, color, (x, row_y_bottom), PIT_RADIUS)
        pit_rects[pit_idx] = pygame.Rect(
            x - PIT_RADIUS, row_y_bottom - PIT_RADIUS, PIT_RADIUS * 2, PIT_RADIUS * 2
        )

        # seed count
        text = font.render(str(state.pits[pit_idx]), True, TEXT_COLOR)
        screen.blit(text, (x - text.get_width() // 2, row_y_bottom - text.get_height() // 2))

        # player 1 pits (top row, right to left)
        pit_idx = 13 - i
        color = PIT_COLOR
        if pit_idx in legal_moves:
            color = HIGHLIGHT_COLOR if selected_pit == pit_idx else (140, 100, 60)

        pygame.draw.circle(screen, color, (x, row_y_top), PIT_RADIUS)
        pit_rects[pit_idx] = pygame.Rect(
            x - PIT_RADIUS, row_y_top - PIT_RADIUS, PIT_RADIUS * 2, PIT_RADIUS * 2
        )

        text = font.render(str(state.pits[pit_idx]), True, TEXT_COLOR)
        screen.blit(text, (x - text.get_width() // 2, row_y_top - text.get_height() // 2))

    # draw current player indicator
    current_color = P0_COLOR if state.current_player == 0 else P1_COLOR
    turn_text = font.render(f"Player {state.current_player}'s turn", True, current_color)
    screen.blit(turn_text, (WINDOW_WIDTH // 2 - turn_text.get_width() // 2, 10))

    return pit_rects


def draw_game_over(screen: pygame.Surface, font: pygame.font.Font, state: BoardState) -> None:
    """Draw game over overlay."""
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    p0_score, p1_score = get_final_scores(state)
    winner = get_winner(state)

    if winner == 0:
        result_text = "Player 0 Wins!"
        color = P0_COLOR
    elif winner == 1:
        result_text = "Player 1 Wins!"
        color = P1_COLOR
    else:
        result_text = "Draw!"
        color = TEXT_COLOR

    big_font = pygame.font.Font(None, 72)
    text = big_font.render(result_text, True, color)
    screen.blit(text, (WINDOW_WIDTH // 2 - text.get_width() // 2, WINDOW_HEIGHT // 2 - 50))

    score_text = font.render(f"Final Score: P0 {p0_score} - {p1_score} P1", True, TEXT_COLOR)
    score_x = WINDOW_WIDTH // 2 - score_text.get_width() // 2
    screen.blit(score_text, (score_x, WINDOW_HEIGHT // 2 + 20))

    restart_text = font.render("Press R to restart or Q to quit", True, TEXT_COLOR)
    screen.blit(
        restart_text, (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, WINDOW_HEIGHT // 2 + 60)
    )


def run_gui(
    p0_type: str = "human",
    p1_type: str = "ai",
    ai_depth: int = 8,
    rules: RuleConfig | None = None,
) -> None:
    """Run the pygame GUI."""
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Congkak")
    font = pygame.font.Font(None, 36)
    clock = pygame.time.Clock()

    if rules is None:
        rules = RuleConfig.default_rules()

    solver = MinimaxSolver(rules, max_depth=ai_depth)
    player_types = [p0_type, p1_type]

    state = BoardState.initial()
    selected_pit: int | None = None
    game_over = False
    ai_thinking = False

    running = True
    while running:
        legal_moves = get_legal_moves(state) if not game_over else []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_r:
                    state = BoardState.initial()
                    game_over = False
                    ai_thinking = False
                    solver.clear_tt()

            if event.type == pygame.MOUSEBUTTONDOWN and not game_over and not ai_thinking:
                current_type = player_types[state.current_player]
                if current_type == "human":
                    pos = pygame.mouse.get_pos()
                    pit_rects = draw_board(screen, font, state, legal_moves, selected_pit)
                    for pit_idx, rect in pit_rects.items():
                        if rect.collidepoint(pos) and pit_idx in legal_moves:
                            result = apply_move(state, pit_idx, rules)
                            state = result.state
                            if is_terminal(state):
                                game_over = True
                            break

        # AI move
        if not game_over and player_types[state.current_player] == "ai" and not ai_thinking:
            ai_thinking = True
            pygame.display.set_caption("Congkak - AI thinking...")
            pit_rects = draw_board(screen, font, state, legal_moves, selected_pit)
            pygame.display.flip()

            move = solver.get_best_move(state)
            if move is not None:
                result = apply_move(state, move, rules)
                state = result.state
                if is_terminal(state):
                    game_over = True

            ai_thinking = False
            pygame.display.set_caption("Congkak")

        # draw
        pit_rects = draw_board(screen, font, state, legal_moves, selected_pit)

        if game_over:
            draw_game_over(screen, font, state)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
