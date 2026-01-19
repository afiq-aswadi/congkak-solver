from collections.abc import Generator

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
from congkak.gui.animation import SowingStep, animate_sowing
from congkak.solver.minimax import MinimaxSolver

# colors
BG_COLOR = (245, 222, 179)  # wheat
BOARD_COLOR = (139, 90, 43)  # saddle brown
PIT_COLOR = (101, 67, 33)  # dark brown
STORE_COLOR = (85, 55, 27)  # darker brown
HIGHLIGHT_COLOR = (255, 215, 0)  # gold
ACTIVE_COLOR = (50, 205, 50)  # lime green - where seed just dropped
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
    pits: list[int] | tuple[int, ...],
    current_player: int,
    legal_moves: list[int],
    selected_pit: int | None,
    active_pit: int | None = None,
    seeds_in_hand: int = 0,
    action: str | None = None,
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
    row_y_top = WINDOW_HEIGHT // 2 - 50
    row_y_bottom = WINDOW_HEIGHT // 2 + 50

    # draw P0's store (left)
    p0_store_color = ACTIVE_COLOR if active_pit == 14 else STORE_COLOR
    p0_store_rect = pygame.Rect(
        BOARD_MARGIN + 20, WINDOW_HEIGHT // 2 - STORE_HEIGHT // 2, STORE_WIDTH, STORE_HEIGHT
    )
    pygame.draw.rect(screen, p0_store_color, p0_store_rect, border_radius=15)
    p0_store_text = font.render(str(pits[14]), True, TEXT_COLOR)
    screen.blit(
        p0_store_text,
        (
            p0_store_rect.centerx - p0_store_text.get_width() // 2,
            p0_store_rect.centery - p0_store_text.get_height() // 2,
        ),
    )
    label = font.render("P0", True, P0_COLOR)
    screen.blit(label, (p0_store_rect.centerx - label.get_width() // 2, p0_store_rect.bottom + 5))

    # draw P1's store (right)
    p1_store_color = ACTIVE_COLOR if active_pit == 15 else STORE_COLOR
    p1_store_rect = pygame.Rect(
        WINDOW_WIDTH - BOARD_MARGIN - STORE_WIDTH - 20,
        WINDOW_HEIGHT // 2 - STORE_HEIGHT // 2,
        STORE_WIDTH,
        STORE_HEIGHT,
    )
    pygame.draw.rect(screen, p1_store_color, p1_store_rect, border_radius=15)
    p1_store_text = font.render(str(pits[15]), True, TEXT_COLOR)
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

        if pit_idx == active_pit:
            color = ACTIVE_COLOR
        elif pit_idx == selected_pit:
            color = HIGHLIGHT_COLOR
        elif pit_idx in legal_moves:
            color = (140, 100, 60)
        else:
            color = PIT_COLOR

        pygame.draw.circle(screen, color, (x, row_y_bottom), PIT_RADIUS)
        pit_rects[pit_idx] = pygame.Rect(
            x - PIT_RADIUS, row_y_bottom - PIT_RADIUS, PIT_RADIUS * 2, PIT_RADIUS * 2
        )

        text = font.render(str(pits[pit_idx]), True, TEXT_COLOR)
        screen.blit(text, (x - text.get_width() // 2, row_y_bottom - text.get_height() // 2))

        # player 1 pits (top row, right to left)
        pit_idx = 13 - i

        if pit_idx == active_pit:
            color = ACTIVE_COLOR
        elif pit_idx == selected_pit:
            color = HIGHLIGHT_COLOR
        elif pit_idx in legal_moves:
            color = (140, 100, 60)
        else:
            color = PIT_COLOR

        pygame.draw.circle(screen, color, (x, row_y_top), PIT_RADIUS)
        pit_rects[pit_idx] = pygame.Rect(
            x - PIT_RADIUS, row_y_top - PIT_RADIUS, PIT_RADIUS * 2, PIT_RADIUS * 2
        )

        text = font.render(str(pits[pit_idx]), True, TEXT_COLOR)
        screen.blit(text, (x - text.get_width() // 2, row_y_top - text.get_height() // 2))

    # draw current player indicator
    current_color = P0_COLOR if current_player == 0 else P1_COLOR
    turn_text = font.render(f"Player {current_player}'s turn", True, current_color)
    screen.blit(turn_text, (WINDOW_WIDTH // 2 - turn_text.get_width() // 2, 10))

    # draw seeds in hand indicator
    if seeds_in_hand > 0:
        hand_text = font.render(f"Seeds in hand: {seeds_in_hand}", True, ACTIVE_COLOR)
        screen.blit(hand_text, (WINDOW_WIDTH // 2 - hand_text.get_width() // 2, WINDOW_HEIGHT - 30))

    # draw action indicator for significant events
    action_labels = {
        "relay": "Relay!",
        "extra_turn": "Extra turn!",
        "capture": "Capture!",
        "forfeit": "Forfeit!",
    }
    if action in action_labels:
        big_font = pygame.font.Font(None, 48)
        action_text = big_font.render(action_labels[action], True, HIGHLIGHT_COLOR)
        screen.blit(
            action_text,
            (WINDOW_WIDTH // 2 - action_text.get_width() // 2, WINDOW_HEIGHT // 2 - 24),
        )

    return pit_rects


def draw_speed_indicator(screen: pygame.Surface, font: pygame.font.Font, delay_ms: int) -> None:
    """Draw animation speed indicator."""
    speed_text = "Speed: instant" if delay_ms == 0 else f"Speed: {delay_ms}ms  [+/-]"
    text = font.render(speed_text, True, (100, 100, 100))
    screen.blit(text, (10, WINDOW_HEIGHT - 30))


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
    animation_delay: int = 0,
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

    # animation state
    animation: Generator[SowingStep, None, None] | None = None
    anim_step: SowingStep | None = None
    anim_player: int = 0
    step_delay = 0
    current_delay = animation_delay  # mutable copy for speed adjustment
    paused = False
    anim_history: list[SowingStep] = []  # history for rewind
    anim_history_idx = 0  # current position in history during replay
    pending_move: int | None = None  # pit selected, waiting to start animation
    pending_move_delay = 0  # countdown before animation starts

    # turn history for rewinding to previous turns
    # each entry: (state_before_move, move, player, animation_steps)
    turn_history: list[tuple[BoardState, int, int, list[SowingStep]]] = []
    pre_anim_state: BoardState | None = None  # state before current animation

    running = True
    while running:
        dt = clock.tick(60)

        # handle animation
        if animation is not None or anim_history_idx < len(anim_history):
            # handle events during animation
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_UP):
                        current_delay = max(0, current_delay - 50)
                    elif event.key in (pygame.K_MINUS, pygame.K_DOWN):
                        current_delay = min(1000, current_delay + 50)
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key in (pygame.K_BACKSPACE, pygame.K_LEFT):
                        if anim_history_idx > 0:
                            # go back one step in current animation
                            anim_history_idx -= 1
                            anim_step = anim_history[anim_history_idx]
                            step_delay = current_delay
                            paused = True
                        elif turn_history:
                            # go back to previous turn
                            prev_state, prev_move, prev_player, prev_steps = turn_history.pop()
                            state = prev_state
                            selected_pit = prev_move
                            anim_player = prev_player
                            anim_history = prev_steps
                            anim_history_idx = len(prev_steps) - 1
                            anim_step = prev_steps[anim_history_idx] if prev_steps else None
                            animation = None
                            pre_anim_state = prev_state
                            step_delay = current_delay
                            paused = True
                            game_over = False
                    elif event.key == pygame.K_RIGHT:
                        # go forward one step
                        if anim_history_idx < len(anim_history):
                            anim_step = anim_history[anim_history_idx]
                            anim_history_idx += 1
                            step_delay = current_delay
                            paused = True
                        elif animation is not None:
                            try:
                                anim_step = next(animation)
                                anim_history.append(anim_step)
                                anim_history_idx = len(anim_history)
                                step_delay = current_delay
                                paused = True
                            except StopIteration:
                                # animation complete
                                pass

            # advance animation if not paused
            if not paused:
                step_delay -= dt
                if step_delay <= 0:
                    # replaying from history or advancing generator
                    if anim_history_idx < len(anim_history):
                        anim_step = anim_history[anim_history_idx]
                        anim_history_idx += 1
                    elif animation is not None:
                        try:
                            anim_step = next(animation)
                            anim_history.append(anim_step)
                            anim_history_idx = len(anim_history)
                        except StopIteration:
                            # save completed turn to history
                            if pre_anim_state is not None and selected_pit is not None:
                                turn_history.append(
                                    (pre_anim_state, selected_pit, anim_player, anim_history.copy())
                                )
                            animation = None
                            anim_step = None
                            anim_history = []
                            anim_history_idx = 0
                            pre_anim_state = None
                            # apply the final state
                            result = apply_move(state, selected_pit, rules)
                            state = result.state
                            selected_pit = None
                            if is_terminal(state):
                                game_over = True
                    else:
                        # finished replaying from history, apply move
                        if pre_anim_state is not None and selected_pit is not None:
                            turn_history.append(
                                (pre_anim_state, selected_pit, anim_player, anim_history.copy())
                            )
                        result = apply_move(state, selected_pit, rules)
                        state = result.state
                        animation = None
                        anim_step = None
                        anim_history = []
                        anim_history_idx = 0
                        pre_anim_state = None
                        selected_pit = None
                        if is_terminal(state):
                            game_over = True

                    # set delay for next step
                    if anim_step is not None:
                        if anim_step.action in ("relay", "extra_turn", "capture", "forfeit"):
                            step_delay = current_delay * 3
                        else:
                            step_delay = current_delay

            # draw animation frame
            if anim_step is not None:
                draw_board(
                    screen,
                    font,
                    anim_step.pits,
                    anim_player,
                    [],
                    None,
                    active_pit=anim_step.current_pos,
                    seeds_in_hand=anim_step.seeds_in_hand,
                    action=anim_step.action,
                )
                draw_speed_indicator(screen, font, current_delay)
                if paused:
                    pause_text = font.render("PAUSED [Space]  [Left/Right]", True, (200, 50, 50))
                    screen.blit(
                        pause_text,
                        (WINDOW_WIDTH // 2 - pause_text.get_width() // 2, WINDOW_HEIGHT - 60),
                    )
            pygame.display.flip()
            continue

        # handle pending move (show selected pit before animation starts)
        if pending_move is not None:
            pending_move_delay -= dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                    running = False

            if pending_move_delay <= 0:
                # start animation
                selected_pit = pending_move
                animation = animate_sowing(state, pending_move, rules)
                anim_history = []
                anim_history_idx = 0
                paused = False
                step_delay = 0
                pending_move = None
                continue  # go to animation handling

            # draw with selected pit highlighted
            draw_board(screen, font, state.pits, state.current_player, [], pending_move)
            draw_speed_indicator(screen, font, current_delay)
            # show "AI plays pit X" indicator
            pit_start, _ = state.player_pit_range(state.current_player)
            pit_label = pending_move - pit_start + 1
            choice_text = font.render(f"AI chooses pit {pit_label}", True, HIGHLIGHT_COLOR)
            screen.blit(
                choice_text,
                (WINDOW_WIDTH // 2 - choice_text.get_width() // 2, WINDOW_HEIGHT // 2 - 24),
            )
            pygame.display.flip()
            continue

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
                    animation = None
                    anim_step = None
                    anim_history = []
                    anim_history_idx = 0
                    turn_history = []
                    pre_anim_state = None
                    solver.clear_tt()
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_UP):
                    current_delay = max(0, current_delay - 50)
                elif event.key in (pygame.K_MINUS, pygame.K_DOWN):
                    current_delay = min(1000, current_delay + 50)
                elif (
                    event.key in (pygame.K_BACKSPACE, pygame.K_LEFT)
                    and turn_history
                    and not ai_thinking
                ):
                    # go back to previous turn from normal state
                    prev_state, prev_move, prev_player, prev_steps = turn_history.pop()
                    state = prev_state
                    selected_pit = prev_move
                    anim_player = prev_player
                    anim_history = prev_steps
                    anim_history_idx = len(prev_steps) - 1
                    anim_step = prev_steps[anim_history_idx] if prev_steps else None
                    animation = None
                    pre_anim_state = prev_state
                    step_delay = current_delay
                    paused = True
                    game_over = False
                    break  # exit event loop to enter animation mode

            if event.type == pygame.MOUSEBUTTONDOWN and not game_over and not ai_thinking:
                current_type = player_types[state.current_player]
                if current_type == "human":
                    pos = pygame.mouse.get_pos()
                    pit_rects = draw_board(
                        screen, font, state.pits, state.current_player, legal_moves, selected_pit
                    )
                    for pit_idx, rect in pit_rects.items():
                        if rect.collidepoint(pos) and pit_idx in legal_moves:
                            if current_delay > 0:
                                pre_anim_state = state
                                selected_pit = pit_idx
                                anim_player = state.current_player
                                animation = animate_sowing(state, pit_idx, rules)
                                anim_history = []
                                anim_history_idx = 0
                                paused = False
                                step_delay = 0
                            else:
                                # instant mode: generate animation for history, then apply
                                steps = list(animate_sowing(state, pit_idx, rules))
                                turn_history.append((state, pit_idx, state.current_player, steps))
                                result = apply_move(state, pit_idx, rules)
                                state = result.state
                                if is_terminal(state):
                                    game_over = True
                            break

        # if we just restored animation state, skip to animation handling
        if anim_history:
            continue

        # AI move
        if not game_over and player_types[state.current_player] == "ai" and not ai_thinking:
            ai_thinking = True
            pygame.display.set_caption("Congkak - AI thinking...")
            draw_board(screen, font, state.pits, state.current_player, legal_moves, selected_pit)
            pygame.display.flip()

            move = solver.get_best_move(state)
            if move is not None:
                if current_delay > 0:
                    # show selected pit first, then start animation
                    pre_anim_state = state
                    pending_move = move
                    pending_move_delay = current_delay * 3
                    anim_player = state.current_player
                else:
                    # instant mode: generate animation for history, then apply
                    steps = list(animate_sowing(state, move, rules))
                    turn_history.append((state, move, state.current_player, steps))
                    result = apply_move(state, move, rules)
                    state = result.state
                    if is_terminal(state):
                        game_over = True

            ai_thinking = False
            pygame.display.set_caption("Congkak")

        # draw
        draw_board(screen, font, state.pits, state.current_player, legal_moves, selected_pit)
        draw_speed_indicator(screen, font, current_delay)

        if game_over:
            draw_game_over(screen, font, state)

        pygame.display.flip()

    pygame.quit()
