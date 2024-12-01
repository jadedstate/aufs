class TilePlacement:
    def __init__(self, x_tiles, y_tiles, origin='top_left', traversal='column_by_column'):
        """
        Initializes the TilePlacement class.
        
        :param x_tiles: Number of tiles along the x-axis (columns).
        :param y_tiles: Number of tiles along the y-axis (rows).
        :param origin: The origin point of the grid. Options are 'top_left' or 'bottom_left'.
        :param traversal: The order in which tiles are traversed. Options are 'column_by_column', 
                          'row_by_row', 'row_by_row_bounce', 'column_by_column_bounce'.
        """
        self.x_tiles = x_tiles
        self.y_tiles = y_tiles
        self.origin = origin
        self.traversal = traversal

    def generate_tile_placements(self):
        """
        Generates a list of tile placements.
        
        :return: A list of tuples where each tuple contains (tile_number, row, column).
        """
        placements = []

        for x in range(self.x_tiles):
            for y in range(self.y_tiles):
                if self.traversal == 'column_by_column':
                    tile_number = y + x * self.y_tiles
                elif self.traversal == 'row_by_row':
                    tile_number = x + y * self.x_tiles
                elif self.traversal == 'row_by_row_bounce':
                    if y % 2 == 0:  # Normal order
                        tile_number = x + y * self.x_tiles
                    else:  # Reverse order
                        tile_number = (self.x_tiles - 1 - x) + y * self.x_tiles
                elif self.traversal == 'column_by_column_bounce':
                    if x % 2 == 0:  # Normal order
                        tile_number = y + x * self.y_tiles
                    else:  # Reverse order
                        tile_number = (self.y_tiles - 1 - y) + x * self.y_tiles
                else:
                    raise ValueError("Traversal method not supported.")

                # Adjust for origin if necessary
                if self.origin == 'bottom_left':
                    row = (self.y_tiles - 1) - y
                else:
                    row = y

                placements.append((tile_number, row, x))

        return placements
