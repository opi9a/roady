
class Rect:
    """ 
    To hold dimensions of a rect, completing any missing
    """
    def __init__(self, bottom=None, top=None, height=None,
                 left=None, right=None, width=None):
        # if bottom is None and (top and height):
        #     self.bottom = top - height
        if top is None and (bottom and height):
            top = bottom + height
        elif height is None and (bottom and top):
            height = top - bottom

        if left is None and (right and width):
            left = right - width
        elif right is None and (left and width):
            right = left + width
        elif width is None and (left and right):
            width = right - left

        self._bottom = bottom
        self._top = top
        self._height = height
        self._left = left
        self._right = right
        self._width = width

    def check(self):
        if not self.ok:
            raise ValueError('this rect is wrong')

    @property
    def bottom(self):
        if self._bottom is not None:
            return self._bottom
        if self._bottom is None and (self._top and self._height):
            return self._top - self._height

    @bottom.setter
    def bottom(self, value):
        self._bottom = value


    @property
    def top(self):
        if self._top is not None:
            return self._top
        if self._top is None and (self._bottom and self._height):
            return self._bottom + self._height

    @top.setter
    def top(self, value):
        self._top = value


    @property
    def height(self):
        if self._height is not None:
            return self._height
        if self._height is None and (self._bottom and self._top):
            return self._top - self._bottom

    @height.setter
    def height(self, value):
        self._height = value


    @property
    def left(self):
        if self._left is not None:
            return self._left
        if self._left is None and (self._right and self._width):
            return self._right - self._width

    @left.setter
    def left(self, value):
        self._left = value


    @property
    def right(self):
        if self._right is not None:
            return self._right
        if self._right is None and (self._left and self._width):
            return self._left + self._width

    @right.setter
    def right(self, value):
        self._right = value


    @property
    def width(self):
        if self._width is not None:
            return self._width
        if self._width is None and (self._left and self._right):
            return self._right - self._left

    @width.setter
    def width(self, value):
        self._width = value


    @property
    def ok(self):
        """ 
        Checks the dims are all available and consistent
        """

        try:
            assert self.top - self.bottom == self.height
        except:
            print('problem with y axis')
            return False

        try:
            assert self.right - self.left == self.width
        except:
            print('problem with x axis')
            return False

        return True

    def __repr__(self):
        return (
            "Rect("
            f"bottom={self.bottom}, "
            f"top={self.top}, "
            f"height={self.height}, "
            f"left={self.left}, "
            f"right={self.right}, "
            f"width={self.width}"
            ")"
        )


