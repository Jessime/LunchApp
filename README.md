# LunchApp

A voting webapp to help make group decisions.

## About

This app attempts to solve the problem of a group of people trying to choose between a set of options.
I specifically used it to help the young adults decide where to go to lunch on Sunday. 

Each user has 10 points to spend in whatever configuration they'd like. All 10 votes can be allocated to a single choice, or spread across multiple choices. 

The app then makes a choice for the group based on a weighted probability from the sum of all votes. 

## Usage

At least for now, there's an instance running at:

https://lunch-app-upc.herokuapp.com

It's running on a free "Dyno", so the initial startup of the app is particularly slow.

### Running it yourself

See the section below on warnings to see why this probably isn't a great idea. If you do want to try it out, you can play with it locally by cloning this repo then running:

```
$ pip install -r requirements.txt
$ python lunch.py
```

If for some crazy reason you want to host it yourself, your best bet is to use Heroku as well. Here are some docs to get you started if you haven't tried it before:

https://devcenter.heroku.com/articles/getting-started-with-python#introduction

## Warnings

This was my first attempt at a webapp. It's hacky. I'm adding it to github primarily for its "historical significance." Here is an incomplete list of some of the weird things going on in the code:

* While the group password matters, user passwords are not actually used in any capacity.
* There's no clean way to switch between users. It's basically "one device: one user."
* I'm not using a database. I have a `Data` class that's a database replacement.
* I'm reading and writing plain-text .csv file hosted on Dropbox. 
* This was my first time writing javascript, so who knows what's happening there.
* Creating new groups hasn't been extensively tested.
* The `pandas` dependency can be difficult to install. 

Bonus: Documentation is pretty non-existent.

## Conclusion

Despite these fairly large behind-the-scenes issues, the app was used successfully by the group for a full summer (until fantasy football took over).

