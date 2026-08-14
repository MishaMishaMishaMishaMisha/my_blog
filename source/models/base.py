from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import String

from source.core.types import str_20, str_50, str_120, str_256


class BaseORMModel(DeclarativeBase):

    type_annotation_map = {str_20: String(20), 
                           str_50: String(50),
                           str_120: String(120),
                           str_256: String(256)}

    # переопределим repr для вывода в print
    repr_columns_num = 2
    repr_additional_columns = ()
    def __repr__(self):
        columns = []
        for index, column in enumerate(self.__table__.columns.keys()):
            if column in self.repr_additional_columns or index < self.repr_columns_num:
                columns.append(f"{column}={getattr(self, column)}")
        return f"<{self.__class__.__name__} {', '.join(columns)}>"
    
    # вернуть модель в виде словаря
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


