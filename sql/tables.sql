/*
 season,game_overall,game_date,game_number,stake,winner,is_placings,Cedric,Dale-O,Knottorious,El-Craigo,Nik

 */
CREATE TABLE game
(
    game_overall int identity
        CONSTRAINT pk_game PRIMARY KEY,
    season       int,
    game_date    date,
    game_number  int,
    stake        int,
    winner       varchar(64),
    is_placings  int,
    cedric       int,
    daleo        int,
    knottorious  int,
    elcraigo     int,
    nik          int
)
GO

CREATE VIEW vw_game as
SELECT game_overall,
       season,
       game_date,
       game_number,
       stake,
       winner,
       is_placings,
       cedric      as [Cedric],
       daleo       as [Dale-O],
       knottorious as [Knottorious],
       elcraigo    as [El-Craigo],
       nik         as [Nik]
FROM game