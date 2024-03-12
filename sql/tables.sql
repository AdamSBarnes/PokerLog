create table event
(
    event_id    int identity
        primary key,
    season_id   int,
    event_date  date     default getdate(),
    is_online   bit      default 1,
    is_person   bit      default null,
    modify_date datetime default getdate()
)
go

create table game
(
    game_id           int identity
        primary key,
    event_id          int,
    buy_in            int,
    stack             int         default 2500,
    blind_timing      int         default 12,
    blind_start       varchar(12) default '25/50',
    blind_end         varchar(12) default '400/800',
    start_time        datetime,
    end_time          datetime,
    is_in_progress    bit,
    is_placing_ranked bit,
    modify_date       datetime    default getdate()
)
go

create table game_player
(
    game_player_id int identity
        primary key,
    game_id        int,
    player_id      int,
    placing        int,
    is_winner      bit,
    modify_date    datetime default getdate()
)
go

create table log
(
    log_id       int identity
        primary key,
    log_contents nvarchar(max),
    log_time     datetime default getdate()
)
go

create table player
(
    player_id       int identity
        primary key,
    player_name     varchar(128),
    player_nickname varchar(128),
    modify_date     datetime default getdate()
)
go

create table season
(
    season_id      int identity
        primary key,
    season_name    varchar(128),
    is_in_progress bit,
    modify_date    datetime default getdate()
)
go