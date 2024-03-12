
create OR ALTER procedure dbo.sp_add_game @game_config nvarchar(max) AS
BEGIN
    INSERT INTO dbo.log(log_contents) VALUES (@game_config);

    DROP TABLE IF EXISTS #data
    SELECT *
    INTO #data
    FROM openjson(@game_config) with (
        season_id INT,
        event_date date,
        is_online bit,
        buy_in int,
        stack int,
        blind_start varchar(20),
        blind_end varchar(20),
        blind_time int,
        is_ranked bit,
        players NVARCHAR(MAX) as json )

    DECLARE @season_id INT,
        @event_date date,
        @is_online bit,
        @buy_in int,
        @blind_start varchar(20),
        @blind_end varchar(20),
        @blind_time int,
        @is_ranked bit,
        @stack int,
        @event_id int,
        @game_id int;


    SELECT @season_id = season_id
    from #data;
    SELECT @event_date = event_date
    from #data;
    SELECT @is_online = is_online
    FROM #data
    SELECT @buy_in = buy_in
    FROM #data
    SELECT @blind_start = blind_start
    FROM #data
    SELECT @blind_end = blind_end
    FROM #data
    SELECT @blind_time = blind_time
    FROM #data
    SELECT @is_ranked = is_ranked
    FROM #data
    SELECT @stack = stack
    FROM #data


-- does an event exist?
    IF NOT EXISTS(
            SELECT 1
            FROM dbo.event
            where event_date = @event_date
        )
        insert into dbo.event(season_id, event_date, is_online)
        values (@season_id, @event_date, @is_online)

    select @event_id = event_id
    from dbo.event
    where event_date = event_date;

    IF EXISTS(SELECT 1
              FROM dbo.game
              WHERE is_in_progress = 1)
        BEGIN
            RAISERROR ( 'Game already in progress',16,1)
        END;


    INSERT INTO dbo.game(event_id, buy_in, stack, blind_timing, blind_start, blind_end, start_time, is_in_progress,
                         is_placing_ranked)
    VALUES (@event_id,
            @buy_in,
            @stack,
            @blind_time,
            @blind_start,
            @blind_end,
            DATEADD(HOUR, 10, GETUTCDATE()),
            1,
            @is_ranked)

    SELECT @game_id = @@IDENTITY;

    INSERT INTO dbo.game_player (game_id, player_id)
    SELECT @game_id, p.value as player_id
    FROM #data
             outer apply openjson(players) p
end;

go
CREATE OR ALTER PROCEDURE dbo.sp_end_game @ranks NVARCHAR(max) AS
BEGIN

    IF NOT EXISTS(SELECT 1
                  FROM dbo.game
                  WHERE is_in_progress = 1)
        BEGIN
            RAISERROR ( 'No Game in progress',16,1)
        END;

    DECLARE @game_id int;

    SELECT @game_id = game_id
    FROM dbo.game
    WHERE is_in_progress = 1;

    UPDATE dbo.game SET end_time = DATEADD(HOUR, 10, GETUTCDATE()), is_in_progress = 0;

    WITH game_ranks as (SELECT r.[key] + 1            as placing,
                               r.value                as player_id,
                               iif(r.[key] = 0, 1, 0) as is_winner,
                               @game_id               as game_id

                        FROM openjson(@ranks) WITH (ranking nvarchar(max) as json) e
                                 outer apply openjson(e.ranking) r)
    UPDATE GP
    SET gp.placing   = gr.placing,
        gp.is_winner = gr.is_winner
    FROM dbo.game_player GP
             JOIN game_ranks GR on gp.player_id = gr.player_id
        AND gr.game_id = gp.game_id
END