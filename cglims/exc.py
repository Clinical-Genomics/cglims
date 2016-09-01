# -*- coding: utf-8 -*-


class LimsException(Exception):
    pass


class MissingLimsDataException(LimsException, KeyError):
    pass


class LimsSampleNotFoundError(LimsException):
    pass


class LimsCaseIdNotFoundError(LimsException):
    pass


class LimsSampleCancelled(LimsException):
    pass


class MultipleSamplesError(LimsException):
    pass
