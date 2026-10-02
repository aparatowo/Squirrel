# text_layout.py - lay a multi-line text out in rows of a fixed width, and move a cursor through them
#
# Pure functions, no display: the note editor uses them to wrap long lines at spaces, to find the row the
# cursor is on, and to move it up and down by SCREEN rows (not by lines of text).
#
# A text is a list of lines.  A row is (line index, start, end): the characters line[start:end].
# The cursor is (line, col) with 0 <= col <= len(line); col == len(line) is "after the last character".


def wrap_line(text, width):
    """[(start, end)] pieces of one line, each at most `width` long, broken after a space where there is one."""
    n = len(text)
    if n <= width:
        return [(0, n)]
    rows, start = [], 0
    while n - start > width:
        end = start + width
        cut = text.rfind(" ", start + 1, end)          # a space inside the row, but not its first character
        if cut > start:
            end = cut + 1
        rows.append((start, end))
        start = end
    rows.append((start, n))
    return rows


def layout(lines, width):
    rows = []
    for index, text in enumerate(lines):
        for start, end in wrap_line(text, width):
            rows.append((index, start, end))
    return rows


def locate(rows, line, col):
    """(row index, column within the row) of the cursor.

    A cursor at the join of two wrapped rows belongs to the second one; at the end of a line, to its last row."""
    last = 0
    for i, (index, start, end) in enumerate(rows):
        if index != line:
            continue
        last = i
        if start <= col < end:
            return i, col - start
    return last, col - rows[last][1]


def move_vertical(rows, line, col, delta, want):
    """The cursor `delta` rows up (-1) or down (+1), aiming for column offset `want`.  Stays put at the edges."""
    row, _offset = locate(rows, line, col)
    target = row + delta
    if target < 0 or target >= len(rows):
        return line, col
    index, start, end = rows[target]
    ends_line = target + 1 >= len(rows) or rows[target + 1][0] != index
    limit = end - start if ends_line else max(0, end - start - 1)    # on a wrapped row the join belongs to the next row
    return index, start + min(want, limit)


def scroll_to(top, row, visible, total):
    """New first visible row so that `row` is on screen (and no blank space is left at the bottom)."""
    if row < top:
        top = row
    elif row >= top + visible:
        top = row - visible + 1
    return max(0, min(top, max(0, total - visible)))
