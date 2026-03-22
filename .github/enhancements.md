# Enhancements
- Remove any trace of the old shiny app
- The general website should not require auth to access, but an adminstrator should be able to auth and add game history to the database
- Administrator should also be able to add new players.
- Authentication should be simple as it will only ever be used by one user.
- The game result adding function needs to allow for an abribtrary selection of players, and then allow creating a new result with a finish order. entered data needs to capture the database fields.
  - The database structure may need to change to allow this. Currently players are set as columns, but this is not likely to be flexible enough for an arbitrary number of players. A more normalized structure with a separate table for players and a join table for game results may be necessary.
  - Admin should also be able to update or delete existing game results, as well as update player information.