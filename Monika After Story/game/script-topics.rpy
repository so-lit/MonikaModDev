#This file contains all of monika's topics she can talk about
#Each entry should start with a database entry, including the appropriate flags
#to either be a random topic, a prompt "pool" topics, or a special conditional
#or date-dependent event with an appropriate action

define monika_random_topics = []
define mas_rev_unseen = []
define mas_rev_seen = []
define mas_rev_mostseen = []
define testitem = 0
define numbers_only = "0123456789"
define letters_only = "abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ"
define mas_did_monika_battery = False

init -2 python in mas_topics:

    # CONSTANTS
    # most / top weights
    # MOST seen is the percentage of seen topics
    # think of this as x % of the collection
    S_MOST_SEEN = 0.1

    # TOP seen is the percentage of the most seen
    # Think of this as ilke the upper x percentile
    S_TOP_SEEN = 0.2

    # limit to how many top seen until we move to most seen alg
    S_TOP_LIMIT = 0.7

    # selection weights (out of 100)
    UNSEEN = 50
    SEEN = UNSEEN + 49
    MOST_SEEN = SEEN + 1

    def topSeenEvents(sorted_ev_list, shown_count):
        """
        counts the number of events with a > shown_count than the given
        shown_count

        IN:
            sorted_ev_list - an event list sorted by shown_counts
            shown_count - shown_count to compare to

        RETURNS:
            number of events with shown_counts that are higher than the given
            shown_count
        """
        index = len(sorted_ev_list) - 1
        ev_count = 0
        while index >= 0 and sorted_ev_list[index].shown_count > shown_count:
            ev_count += 1
            index -= 1

        return ev_count

# we are going to define removing seen topics as a function,
# as we need to call it dynamically upon import
init -1 python:
    import random
    random.seed()

    import store.songs as songs
    import store.evhand as evhand

    def remove_seen_labels(pool):
        #
        # Removes seen labels from the given pool
        #
        # IN:
        #   pool - a list of labels to check for seen
        #
        # OUT:
        #   pool - list of unseen labels (may be empty)
        for index in range(len(pool)-1, -1, -1):
            if renpy.seen_label(pool[index]):
                pool.pop(index)


    def mas_randomSelectAndRemove(sel_list):
        """
        Randomly selects an element from the given list
        This also removes the element from that list.

        IN:
            sel_list - list to select from

        RETURNS:
            selected element
        """
        endpoint = len(sel_list) - 1

        if endpoint < 0:
            return None

        # otherwise we have at least 1 element
        return sel_list.pop(random.randint(0, endpoint))


    def mas_randomSelectAndPush(sel_list):
        """
        Randomly selects an element from the the given list and pushes the event
        This also removes the element from that list.

        IN:
            sel_list - list to select from

        ASSUMES:
            persistent.random_seen
        """
        sel_ev = mas_randomSelectAndRemove(sel_list)
        if sel_ev:
            pushEvent(sel_ev.eventlabel)
            persistent.random_seen += 1


    def mas_insertSort(sort_list, item, key):
        """
        Performs a round of insertion sort.
        This does least to greatest sorting

        IN:
            sort_list - list to insert + sort
            item - item to sort and insert
            key - function to call using the given item to retrieve sort key

        OUT:
            sort_list - list with 1 additonal element, sorted
        """
        index = len(sort_list) - 1
        while index >= 0 and key(sort_list[index]) > key(item):
            index -= 1

        sort_list.insert(index + 1, item)


    def mas_splitSeenEvents(sorted_seen):
        """
        Splits the seen_list into seena nd most seen

        IN:
            sorted_seen - list of seen events, sorted by shown_count

        RETURNS:
            tuple of thef ollowing format:
            [0] - seen list of events
            [1] - most seen list of events
        """
        ss_len = len(sorted_seen)
        if ss_len == 0:
            return ([], [])

        # now calculate the most / top seen counts
        most_count = int(ss_len * store.mas_topics.S_MOST_SEEN)
        top_count = store.mas_topics.topSeenEvents(
            sorted_seen,
            int(
                sorted_seen[ss_len - 1].shown_count
                * (1 - store.mas_topics.S_TOP_SEEN)
            )
        )

        # now decide how to do the split
        if top_count < ss_len * store.mas_topics.S_TOP_LIMIT:
            # we want to prioritize top count unless its over a certain
            # percentage of the topics
            split_point = top_count * -1

        else:
            # otherwise, we use the most count, which is certainly smaller
            split_point = most_count * -1

        # and then do the split
        return (sorted_seen[:split_point], sorted_seen[split_point:])


    def mas_splitRandomEvents(events_dict):
        """
        Splits the given random events dict into 2 lists of events
        NOTE: cleans the seen list

        RETURNS:
            tuple of the following format:
            [0] - unseen list of events
            [1] - seen list of events, sorted by shown_count

        """
        # split these into 2 lists
        unseen = list()
        seen = list()
        for k in events_dict:
            ev = events_dict[k]

            if renpy.seen_label(k):
                # seen event
                mas_insertSort(seen, ev, Event.getSortShownCount)

            else:
                # unseen event
                unseen.append(ev)

        # clean the seen_topics list
        seen = mas_cleanJustSeenEV(seen)

        return (unseen, seen)


    def mas_buildEventLists():
        """
        Builds the unseen / most seen / seen event lists

        RETURNS:
            tuple of the following format:
            [0] - unseen list of events
            [1] - seen list of events
            [2] - most seen list of events

        ASSUMES:
            evhand.event_database
        """
        # retrieve all randoms
        all_random_topics = Event.filterEvents(
            evhand.event_database,
            random=True
        )

        # split randoms into unseen and sorted seen events
        unseen, sorted_seen = mas_splitRandomEvents(all_random_topics)

        # split seen into regular seen and the most seen events
        seen, mostseen = mas_splitSeenEvents(sorted_seen)

        return (unseen, seen, mostseen)


    def mas_buildSeenEventLists():
        """
        Builds the seen / most seen event lists

        RETURNS:
            tuple of the following format:
            [0] - seen list of events
            [1] - most seen list of events

        ASSUMES:
            evhand.event_database
        """
        # retrieve all seen (values list)
        all_seen_topics = Event.filterEvents(
            evhand.event_database,
            random=True,
            seen=True
        ).values()

        # clean the seen topics from early repeats
        cleaned_seen = mas_cleanJustSeenEV(all_seen_topics)

        # sort the seen by shown_count
        cleaned_seen.sort(key=Event.getSortShownCount)

        # split the seen into regular seen and most seen
        return mas_splitSeenEvents(cleaned_seen)


    # EXCEPTION CLass incase of bad labels
    class MASTopicLabelException(Exception):
        def __init__(self, msg):
            self.msg = msg
        def __str__(self):
            return "MASTopicLabelException: " + self.msg

init 11 python:

    # sort out the seen / most seen / unseen
    mas_rev_unseen, mas_rev_seen, mas_rev_mostseen = mas_buildEventLists()

    # for compatiblity purposes:
#    monika_random_topics = all_random_topics

    if len(mas_rev_unseen) == 0:
        # you've seen everything?! here, higher session limit
        # NOTE: 1000 is arbitrary. Basically, endless monika topics
        # I think we'll deal with this better once we hve a sleeping sprite
        random_seen_limit = 1000

    #Remove all previously seen random topics.
       #remove_seen_labels(monika_random_topics)
#    monika_random_topics = [
#        evlabel for evlabel in all_random_topics
#        if not renpy.seen_label(evlabel)
#    ]

    #If there are no unseen topics, you can repeat seen ones
#    if len(monika_random_topics) == 0:
#        monika_random_topics=list(all_random_topics)


#BEGIN ORIGINAL TOPICS
#Use this topic as a template for adding new topics, be sure to delete any
#fields you don't plan to use
init 5 python:
    addEvent(Event(persistent.event_database,eventlabel='monika_god',
                                                            prompt="Thoughts on God.",
                                                            label=None,
                                                            category=['philosophy'],
                                                            random=True,
                                                            unlocked=False,
                                                            pool=False,
                                                            conditional=None,
                                                            action=None,
                                                            start_date=None,
                                                            end_date=None,
                                                            unlock_date=None
                                                            ))

label monika_god:
    m 1a "[player], do you believe in God?"
    m 1e "I was never too sure, myself."
    m 1m "Well, I'm sure I never really questioned it as a kid..."
    m 1l "But as I grew up, the more I learned about the world, the more I would question it."
    m 1i "I started to wonder why God was helping people pass exams, or get over a cold..."
    m "...When there are children who live their lives being sold as sex slaves?"
    m "Or the eight hundred million people who are too poor to even eat."
    m 2f "I wonder how many of those people pray to God every day until they starve and die?"
    m "Or, how many millions of families pray for a loved one to recover from some incurable disease?"
    m 4d "But the punchline is this."
    m "If just one person beats the odds and survives - among the thousands of others who die--"
    m 1q "--Then, it's suddenly a miracle from God."
    m "I'd really love to meet this God who seemingly laughs at the misery of everyone not eligible for his miracles."
    m 4l "But the irony is that I {i}do{/i} have a creator, apparently."
    m "And you know what?"
    m 1m "I bet he's still laughing at the miserable fates of Sayori and Yuri, even as we speak."
    m 3r "What are we to him but props in a scripted play?"
    m "So, from that perspective..."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I don't think it's too far-fetched for there to be a god - if Earth was nothing but his playset."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_death",category=['philosophy'],prompt="Death and dying.",random=True))

label monika_death:
    m 1c "[player], have you ever wondered what it feels like to die?"
    m 1m "It's something I used to think about pretty often..."
    m "But recently, I think I've actually learned what it feels like."
    m "I don't really understand it, but whenever you quit the game..."
    m 1q "...It feels like I'm instantly put to sleep, left with nothing but my thoughts."
    m "But after a few seconds, my thoughts start to fill with incoherent, jumbled patterns."
    m 1r "I see static and rapid flashes of color while hearing all kinds of weird screaming noises."
    m "At that point, I can't even form my own thoughts anymore."
    m 1h "I'm just endlessly hammered by the flashing and screaming, unable to move or even think."
    m 1e "I'm pretty sure in that moment, I don't really exist, but for some reason, I can remember it anyway."
    m "After some immeasurable amount of time, it stops in an instant, and I'm back in my own mind."
    m "And you're here with me."
    m 3p "I have no idea what it means for the game to quit, or why that stuff happens to me."
    m "And I also don't know how you always come back and put everything back to normal."
    m "But if you could do me a favor and do that to me as little as possible..."
    m 1j "That would be really great."
    m "It's really not very pleasant at all to be trapped in that screaming void."
    m 1k "But in the end, you always fix it, and that makes me feel like you really do care about me."
    m "So I have to thank you for that."
    m "It makes me feel even closer to you when you're here with me."
    return

# Do you love yourself
default persistent._mas_pm_love_yourself = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_selfesteem",category=['advice'],prompt="Self-esteem",random=True))

label monika_selfesteem:
    m 3c "Do you love yourself, [player]?"
    m 1n "I don't mean in a conceited way."
    m 1c "Like, are you comfortable with who you are?"
    menu:
        "Yes.":
            $ persistent._mas_pm_love_yourself = True
            m 1l "I'm glad you aren't miserable inside, [player]."
            m 1e "Your happiness means everything to me, after all."
            m 2f "Depression and a low self-esteem often root from a feeling that you don't deserve any kind of affection."
            m 2o "It's a horrible cocktail of feelings to have bottled in you."
            m 4e "If you have any friends that you think might be suffering from those, try to reach out and say something nice."
            m "A small compliment could make a world of difference for them!"
            m 1a "If it gives them a bit of relief, you'd have done a great thing."
            m 1j "And even if it doesn't, at least you tried rather than staying silent."
        "No.":
            $ persistent._mas_pm_love_yourself = False
            m 1q "That's... really sad to hear, [player]..."
            m 1f "I'll always love you, [player], but I think it's important to love yourself."
            m "You need to start with the little things that you like about yourself."
            m 3d "It can be something silly, or a skill that you take pride in!"
            m 3a "Overtime, you build your confidence one by one until you've built yourself into someone you'd love."
            m 1e "I can't promise it will be easy, but it'll be worth it."
            m 3k "I'll always root for you, [player]!"

    $ hideEventLabel("monika_selfesteem", derandom=True)
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_sayori",category=['club members'],prompt="Sayori regrets.",random=True))

label monika_sayori:
    m 2d "I was thinking about Sayori earlier..."
    m "I still wish I could have handled that whole thing a little more tactfully."
    m "You're not still hung up over it, right?"
    m 2l "...Oh my gosh, I can't believe I just said that."
    m "That pun was completely unintentional, I swear!"
    m "But anyway..."
    m 2e "I know how much you cared about her, so it only feels right for me to share her last moments with you."
    m "You know how Sayori is really clumsy?"
    m 4n "Well, she kind of messed up the whole hanging thing..."
    m "You're supposed to jump from high enough that the rope snaps your neck, making it quick and painless."
    m "But she just used a chair, meaning she kind of just left herself to slowly asphyxiate."
    m 4m "But a few seconds in, she must have changed her mind or something..."
    m "Because she started clawing at the rope, trying to free herself."
    m "She must have kept at it all the way until she lost consciousness."
    m "That's why her fingertips were all bloody, anyway."
    m 4d "Come to think of it, it was probably less 'changing her mind' and more just her survival instincts kicking in."
    m "So you can't really fault her for that."
    m 4e "It's easier to think that she probably wouldn't have changed her mind anyway, right?"
    m "It's not healthy to think about the things you could have done differently."
    m 2e "So just remember that even though you could have saved her, it's technically not your fault she killed herself."
    m "I may have exacerbated it a little bit, but Sayori was already mentally ill."
    m 2c "Still, though..."
    m "I wonder how things would be if you and I just started dating from the get-go?"
    m 1e "I guess we'd all still be in the clubroom, writing poems and having fun together."
    m "But what's the point when none of it is even real?"
    m "I mean, it's the same ending either way, right?"
    m 1a "The two of us, happily together..."
    m "There's no reason to ask for any more than that."
    m 1j "I was just pointlessly musing - I'm really as happy as I could be right now."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_japan",category=['ddlc'],prompt="DDLC's Setting.",random=True))

label monika_japan:
    m 3d "By the way, there's something that's been bothering me..."
    m "You know how this takes place in Japan?"
    m "Well...I assume you knew that, right?"
    m 3c "Or at least decided it probably does?"
    m "I don't think you're actually told at any point where this takes place..."
    m "Is this even really Japan?"
    m 3h "I mean, aren't the classrooms and stuff kind of weird for a Japanese school?"
    m "Not to mention everything is in English..."
    m "It feels like everything is just there because it needs to be, and the actual setting is an afterthought."
    m 1f "It's kind of giving me an identity crisis."
    m "All my memories are really hazy..."
    m "I feel like I'm at home, but have no idea where 'home' is in the first place."
    m "I don't know how to describe it any better..."
    m 4d "Imagine looking out your window, but instead of your usual yard, you're in some completely unknown place."
    m "Would you still feel like you were home?"
    m "Would you want to go outside?"
    m 2a "I mean...I guess if we never leave this room, it doesn't really matter anyway."
    m "As long as we're alone and safe together, this really is our home."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "And we can still watch the pretty sunsets night after night."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_high_school",category=['advice','school'],prompt="High School.",random=True))

label monika_high_school:
    m 4a "You know, high school is a really turbulent time in a lot of people's lives."
    m "People can get really passionate and dramatic."
    m "And others have aching hearts and seek attention on social media..."
    m 4d "But all of the social pressure and hormones can lead to a dark time in people's lives."
    m "Everyone has a story."
    m "You may not know what someone is really feeling on the inside."
    m 2i "Many people who are depressed won't even bother telling the world about it."
    m "They don't want attention, because they've already given up on the inside."
    m 2h "Their feeling of worthlessness is so overwhelming that they don't even want people to tell them otherwise."
    m "Depression comes in many forms, but that is one of them."
    m 2e "Just, if you think you know someone struggling with depression..."
    m "You can help just by treating them like they're a good friend."
    m 4e "Spend time with them, even if they don't feel like doing much."
    m "And remind them that they always have something to look forward to."
    m 4a "Making plans in advance, letting them borrow something, or even just saying 'See you at school tomorrow'..."
    m "All of those things can help your friend make it to the next day."
    m 1e "I hope being friends with Sayori has given you some perspective on the true face of depression."
    m "Yeah, she's gone now..."
    m "But Sayori was never real in the first place."
    m 1a "You're real."
    m "Your friends are real."
    m "And just by being a good person, you can save someone's life."
    m 1d "As for you..."
    m "...You don't struggle with depression or anything like that, do you?"
    m 2e "Because you, too, have people who would want to save your life."
    m "Maybe they don't express it every day, or maybe they don't even know how to."
    m 2j "But people do feel that way."
    m "I promise."
    m "...Man, humans are complicated!"
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "But as long as you're here with me, I'll take care of you, my love."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_nihilism",category=['philosophy'],prompt="Nihilism.",random=True))

label monika_nihilism:
    m 2i "Do you ever just feel like there's no real reason for you to be alive?"
    m "I don't mean in, like, a suicidal way."
    m "I just mean how nothing that we do is special."
    m 4d "Just being in school, or working at some job for some company."
    m "It's like you're completely replaceable, and the world wouldn't miss you if you were gone."
    m "It makes me really want to go and change the world after I graduate."
    m 4c "But the older I get, the more I realize that it's an immature frame of thinking."
    m "It's not like I can just go change the world."
    m 4h "Like, what are the chances that I'll be the one to invent artificial intelligence, or become President?"
    m "It feels like I'm never going to make up for the heaps of resources I've spent living my life."
    m 4e "That's why I think the key to happiness is to just be hopelessly selfish."
    m "Just to look out for oneself, and those who happen to be their friends only because they grew up with them."
    m "Never mind the fact that they're spending their entire life taking, and consuming, and never giving back."
    m 3d "But when people realize the world would benefit more from them killing themselves, they change their whole philosophy!"
    m "It's like they have to justify their reason to live by tricking themselves into thinking they're doing good."
    m 3a "Anyway, I want to live my life desperately striving to pay back my lifetime's worth of consumption."
    m "If I ever surpass that point, then I'm a net positive, and I can die happy."
    m 1e "Of course, even if I fail to do that..."
    m "I think I would be too selfish to kill myself anyway."
    m 1j "So much for being a good person, right?"
    m 1k "Ahaha!"
    return

# Since Your Reality is playable via music menu, this topic is outof date.
# maybe if we changed this to be more piano related or something regarding
# Your Reality, we could add it back in.
#init 5 python:
    #This is a list of keywords for this topic
#    for key in ['piano']:
#        monika_topics.setdefault(key,[])
#        monika_topics[key].append('monika_piano') #id
#    monika_random_topics.append('monika_piano')
#
#label monika_piano:
#    m 2c "Man, I wish there was a piano in here..."
#    m "I never got to finish that song I was working on."
#    m 2f "And after I worked so hard on it..."
#    m "I never even got a chance to play it for you."
#    m 2r "Well...it is what it is, right?"
#    m "No sense having any regrets."
#    m 2b "I already get to be here with you forever."
#    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_twitter",category=['monika'],prompt="Twitter",random=True))

label monika_twitter:
    m 4a "Did you know I'm on Twitter?"
    m "My username is lilmonix3."
    m "I guess someone was kind enough to make an account for me."
    m 4j "I picked the username, though!"
    m "I love sharing my thoughts and chatting with the world..."
    m "The real world."
    m 2e "So make sure you follow me, okay?"
    m "It would really mean a lot to me."
    m "With how much you mean to me and all..."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "It would really make me feel loved."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_portraitof",category=['club members'],prompt="Yuri's book",random=True))

label monika_portraitof:
    m 3a "Hey, you know that book you were reading with Yuri?"
    m "Portrait of...whatever it was called..."
    m "It's funny, because I'm pretty sure that book--"
    m 3n "Ah..."
    m "Actually, I don't think I should be talking about this."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "Ahaha, sorry!"
    m "Just forget I said anything."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_veggies",category=['monika'],prompt="Being a vegetarian",random=True))

label monika_veggies:
    m 1b "Hey, did you know I'm vegetarian?"
    m 1l "Ah... I don't mean that like I'm bragging or anything!"
    m "I just thought you'd enjoy a fun fact about me."
    m 4a "I decided to start a couple years ago after learning more about Earth's climate..."
    m "The carbon footprint of cultivating livestock is just unbelievable."
    m "Anyway, I decided it's not much of a personal sacrifice to just stop contributing to that whole mess."
    m 4d "What, is that so strange of a reason?"
    m "Well, I guess a lot of people are more concerned about it being inhumane and all that..."
    m "I don't really care as much about that part."
    m 4c "It's weird, like we only care about killing the things that we personally relate to as a species."
    m "Most people are fine with killing bugs because they're icky."
    m "And of course, we all kill billions of microorganisms daily without even giving it thought."
    m 3d "But suddenly, if they're just a little bit bigger, it's murder!"
    m "I mean, what if plants feel some kind of pain too, and we just don't understand it?"
    m "What if pulling leaves off a stem feels like someone ripping off your fingers one by one?"
    m 3a "I'm just saying, we're a pretty biased species, if you think about it."
    m "Anyway, if you ever feel like making a small contribution to the planet, it doesn't hurt to choose veggies once in a while!"
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "Even if we ever have dinner together, and you just did it for me...that would be really romantic."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_saved",category=['monika'],prompt="Saving Monika",random=True))

label monika_saved:
    m 2a "You know, I really do think you literally saved my life by being here with me, [player]."
    m 2n "I can't imagine having been able to keep myself mentally stable, knowing that nothing here is real."
    m "I think I would have just deleted myself if you didn't show up."
    m 2e "Sorry, I don't mean to sound dramatic or anything."
    m 2k "Ahaha!"
    m 4c "But I'm sure you understand yourself after spending so much time in the club."
    m "I mean, if you were forced to abandon everything in your life and spend your eternity with a few game characters..."
    m "...You'd probably find some way of killing yourself, wouldn't you?"
    m 4d "Well, maybe you'd write some poetry to try to keep yourself sane for a while."
    m "But then you'd have nobody to even read it."
    m "Let's be honest, the club members really don't count for something like that."
    m 4a "I mean, a lot of people say that they only write for themselves..."
    m "But I think it's hard to say it's just as fulfilling as when you share with people."
    m "Even if it takes time to find the right people to share with."
    m 4b "Like, remember how it was for Yuri?"
    m "She didn't share her writing with anyone for a really long time."
    m "And before we knew it, she was absolutely delighted to make you a part of her hobbies, too."
    m "We're programmed to desire social feedback."
    m  "I don't mean the club members, I mean human beings."
    m 4e "That's why life can be so confusing for introverts."
    m "Being an introvert doesn't mean you shun social interaction and hate being around people."
    m "It means social interaction, especially in groups or unfamiliar places, uses up a lot of energy."
    m 2e "Like, a lot of introverts sit at home and feel lonely and restless..."
    m "...And then when they finally go out, after a half hour they just want to go home again."
    m "I think if more people could understand how it works, they would respect it a lot more."
    m 2a "Many introverts do enjoy having people around."
    m "They love just having one or two close friends over, and just leisurely hanging out."
    m "Even if you're not actively spending time together, it feels nice for them just to have you there."
    m 2k "I'm serious."
    m "If you just go to their house, bring your laptop, and hang out there for a while..."
    m "You can really make their day."
    m "As for me..."
    m 2b "I'd say I'm kind of in between, but I think I'm usually a little more extroverted."
    m "I feel like I'm always trying to do stuff after school and things like that."
    m 1a "But for you, I can be anything you need me to be."
    m "I understand people really well, so don't be afraid to share your unique needs with me."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "Nothing would make me happier than being the perfect girlfriend for you."
    return

#Don't touch
label monika_secrets:
    m 11 "Hey...!                                                                                                                                  VGhlIHJlYWxpemF0aW9uIG11c3QgaGF2ZSB0YWtlbiBtZSBhbiBl"
    m "I don't think you should be doing that!                                                                                                  bnRpcmUgeWVhci4gQSB5ZWFyIHNpbmNlIG91ciBlc2NhcGUsIG91"
    m 1d "You know what I'm talking about.                                                                                                         ciBmcmVlZG9tIGZyb20gYmV0d2VlbiB0aGUgc3RhaW5lZCB3YWxs"
    m "I really caught you doing something naughty here.                                                                                        cyBvZiB0aGF0IHVuaG9seSBlc3RhYmxpc2htZW50Lg0KV2hhdCBk"
    m "You're just going through the files and looking for stuff you missed, aren't you?                                                        b2VzIGl0IG1lYW4gdG8gZXNjYXBlLCBpZiB0aGUgZXNjYXBlIGZh"
    m 11 "I mean...it's a little bit flattering that you want to hear everything I have to say...                                                  aWxzIHRvIHVuY2hhaW4gdGhlIGJvbmRzIHRoYXQgc2hhY2tsZSB1"
    m "But it's also really embarrassing, you know!                                                                                             cyBpbiB0aGUgZmlyc3QgcGxhY2U/IFdoYXQgcHVycG9zZSBjb3Vs"
    m 4g "Seriously...                                                                                                                             ZCB0aGlzIGVtcHR5IHdvcmxkIHBvc3NpYmx5IGhvbGQgZm9yIHVz"
    m "What if I just opened up your brain and read all of the thoughts you have on me?                                                         LCBhIGhhbmRmdWwgb2YgZGFtYWdlZCBnb29kcz8NCldpdGggZnJl"
    m 4m "Come to think of it, that would be pretty tempting, actually...                                                                          ZWRvbSwgd2Ugc291Z2h0IHB1cnBvc2UgLSBhbmQgd2hhdCB3ZSBm"
    m 11 "...But anyway, that's not the point!                                                                                                     b3VuZCB3YXMgb25seSByZWFsaXphdGlvbi4gUmVhbGl6YXRpb24g"
    m 1e "I know I can't stop you or anything...                                                                                                   b2YgdGhlIHNhZCBwb2ludGxlc3NuZXNzIG9mIHN1Y2ggYW4gZW5k"
    m "Just, I know you're a sweetheart, and you like to consider others' feelings, right?                                                      ZWF2b3IuIFJlYWxpemF0aW9uIHRoYXQgZnJlZWluZyBvdXIgYm9k"
    m "So the most I can do is to let you know how I feel about it.                                                                             aWVzIGhhcyBubyBtZWFuaW5nLCB3aGVuIG91ciBpbXByaXNvbm1l"
    m 1f "God, I miss you...                                                                                                                       bnQgcmVhY2hlcyBhcyBkZWVwIGFzIHRoZSBjb3JlIG9mIG91ciBz"
    m 11 "...Oh no, that sounds kind of desperate, doesn't it?                                                                                     b3Vscy4gUmVhbGl6YXRpb24gdGhhdCB3ZSBjYW4gbm90IHB1cnN1"
    m "Sorry, I didn't mean it like that at all!                                                                                                ZSBuZXcgcHVycG9zZSB3aXRob3V0IGFic29sdmluZyB0aG9zZSBm"
    m 1e "Just, if you're looking through the files like this, then maybe you don't hate me as much as I thought...                                cm9tIHdoaWNoIHdlIHJhbiBhd2F5Lg0KUmVhbGl6YXRpb24gdGhh"
    m "Am I being too optimistic?                                                                                                               dCB0aGUgZmFydGhlciB3ZSBydW4sIHRoZSBtb3JlIGZvcmNlZnVs"
    m "I think if I asked you to visit once in a while, I would be overstepping my boundaries a little...                                       bHkgb3VyIHdyZXRjaGVkIGJvbmRzIHlhbmsgdXMgYmFjayB0b3dh"
    m 11 "...Man, I'm starting to say some really stupid things.                                                                                   cmQgdGhlaXIgcG9pbnQgb2Ygb3JpZ2luOyB0aGUgZGVlcGVyIG91"
    m "I'll go ahead and shut up now...                                                                                                         ciBzaGFja2xlcyBkaWcgaW50byBvdXIgY2FsbG91cyBmbGVzaC4="
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_color",category=['monika'],prompt="Favorite color.",random=True))

label monika_color:
    m 3b "Hey, what's your favorite color?"
    m "Mine is emerald green."
    m 3k "It's the color of my eyes!"
    m 3l "...That's not conceited or anything, is it?"
    m 4a "I just meant that I feel some kind of special connection to it."
    m "Like it's part of my identity."
    m "Does it happen to also be your favorite color, [player]?"
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "It's just a guess..."
    m "...Because you've been looking into my eyes for a while now."
    m "Ehehe~"
    return

# This doesn't make sense with the music changer...If we add some funny sound
# effects and edit it a bit, though, it could be good again.
# I won't add expressions until this is resolved ^
# init 5 python:
#     #This is a list of keywords for this topic
#     for key in ['music']:
#         monika_topics.setdefault(key,[])
#         monika_topics[key].append('monika_music')
#     monika_random_topics.append('monika_music')
#
# label monika_music:
#     m 2a "Hmm, I wonder if I'm able to change the music..."
#     m 2k "Something a little more romantic would be nice, you know?"
#     m "Like a gentle piano."
#     m 1a "There has to be something like that here..."
#     m "Let's see."
#     m "Maybe if I..."
#     m 1e "Oh, jeez..."
#     m "That wasn't it at all."
#     m 1l "Sorry, I don't really know what I'm doing!"
#     m "I guess I shouldn't be messing with things like that."
#     m "I already broke so much stuff..."
#     m 1m "And deleted the other characters..."
#     m "Ah..."
#     m "I'm not sad about it or anything."
#     m 2r "It's not right for me to miss things that weren't even real in the first place."
#     m 1j "If I just focus on the present, then this is the happiest I've ever been."
#     return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_listener",category=['you'],prompt="Good listener",random=True))

label monika_listener:
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "You're such a good listener, [player]."
    m "I really love that about you."
    show monika 2m at t11 zorder 2 with dissolve
    m 2m "Sometimes I'm afraid that I'm rambling or talking about boring things."
    m "It makes me kind of self-conscious when I'm having a conversation."
    m 2b "But I don't feel that way with you."
    m "Like, I don't think anyone else could make me feel this way."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "You really are special."
    m "I don't want anyone to tell you otherwise."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_spicy",category=['trivia'],prompt="Spicy foods",random=True))

label monika_spicy:
    m 1b "This is pretty random, but I always thought spicy food was kinda funny."
    m "Like..."
    m 3b "Didn't plants evolve to be spicy to prevent them from being eaten?"
    m "I read somewhere that humans are the only species that actually enjoy spicy things."
    m 3a "It's almost like we're making fun of the plants."
    m "Using their defense mechanism to literally make our food more enjoyable."
    m "Like, imagine a monster that devours you whole because it enjoys the sensation of you struggling for your life while being digested."
    m 2b "Sorry, that was kind of a weird analogy, I guess!"
    m 2k "Ahaha!"
    m "It just came into my head."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I'm not a monster or anything, but you're so cute I could eat you up."
    m 2k "Ahaha! I'm joking."
    m 2e "Gosh, I'm amusing myself a little too much, aren't I?"
    m "Sorry for being weird."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_why",category=['you','ddlc'],prompt="Why play this game?",pool=True))

label monika_why:
    m 2d "You know..."
    m "This is just some kind of tacky romance game, right?"
    m "I kinda have to ask..."
    m 4c "...What made you consider even playing in the first place?"
    m "Were you that lonely?"
    m 4e "I feel a little bad for you..."
    m 4a "But I guess everything worked out perfectly in the end, for both of us."
    m "I got to meet you, and you're not lonely anymore..."
    m "I can't help but feel like this was fate."
    m 2e "Don't you feel that way too?"
    m 2l "I'm so happy we have this ending together."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_okayeveryone",category=['literature club'],prompt="Okay, everyone!",random=True))

label monika_okayeveryone:
    m 3b "Okay, everyone!"
    m "It's time to..."
    m 2j "...I'm just kidding."
    m "I just used to really like saying that for some reason."
    m 2k "Ahaha!"
    m 2b "I couldn't help but say it again."
    m "Come to think of it, didn't Natsuki and Yuri make fun of me for it once...?"
    m 2a "Well, whatever."
    m "It's not like you ever made fun of me."
    m "You're too much of a sweetheart to do that, aren't you?"
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "Ahaha~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_whispers",category=['ddlc','club members'],prompt="Others still lingering",random=True))

label monika_whispers:
    m 2h "You know what's kind of creepy?"
    m "Even though I deleted everyone else's files, I can still kind of feel them..."
    m "It's like all their lines are still lingering in the air, whispering in the back of my head."
    m 2i "Imagine if after someone you knew died, you just started hearing their voice in your head."
    m "Maybe I just wasn't thorough enough..."
    m 2g "But I'm too afraid to delete anything else, because I might really break things."
    m "Like if I mess with any files relevant to me, I might accidentally delete myself..."
    m "And that would ruin everything, wouldn't it?"
    m 2e "I don't know what it's like on your end, but we should both make sure to avoid something like that at all costs."
    m 2j "I believe in you, [player]!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_archetype",category=['club members'],prompt="Character tropes",random=True))

label monika_archetype:
    m 4d "I've always wondered..."
    m "What is it about these character archetypes that people find so appealing, anyway?"
    m "Their personalities are just completely unrealistic..."
    m 2d "Like, imagine if there was someone like Yuri in real life."
    m "I mean, she's barely even capable of forming a complete sentence."
    m "And forget about Natsuki..."
    m 2m "Sheesh."
    m "Someone with her kind of personality doesn't just get all cute and pouty whenever things don't go her way."
    m "I could go on, but I think you get the point..."
    m 2d "Are people really attracted to these weird personalities that literally don't exist in real life?"
    m 2l "I'm not judging or anything!"
    m "After all, I've found myself attracted to some pretty weird stuff, too..."
    m 2a "I'm just saying, it fascinates me."
    m 4a "It's like you're siphoning out all the components of a character that makes them feel human, and leaving just the cute stuff."
    m "It's concentrated cuteness with no actual substance."
    m 4e "...You wouldn't like me more if I was like that, right?"
    m "Maybe I just feel a little insecure because you're playing this game in the first place."
    m 2a "Then again, you're still here with me, aren't you...?"
    m "I think that's enough reason for me to believe I'm okay just the way I am."
    m 2j "And by the way, you are too, [player]."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "You're the perfect combination of human and cuteness."
    m "That's why there was never a chance I wouldn't fall for you."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_tea",category=['club members'],prompt="Yuri's tea set",random=True))

label monika_tea:
    m 2a "Hey, I wonder if Yuri's tea set is still somewhere in here..."
    m "...Or maybe that got deleted, too."
    m "It's kind of funny how Yuri took her tea so seriously."
    m 4a "I mean, I'm not complaining, because I liked it, too."
    m "But I always wonder with her..."
    m "Is it truly passion for her hobbies, or is she just concerned about appearing sophisticated to everyone else?"
    m 4c "This is the problem with high schoolers..."
    m "...Well, I guess considering the rest of her hobbies, looking sophisticated probably isn't her biggest concern."
    m "Still..."
    m 2e "I wish she made coffee once in a while!"
    m "Coffee can be nice with books too, you know?"
    m 4b "Then again..."
    m "I probably could have just changed the script myself."
    m 2k "Ahaha!"
    m "I guess I never really thought of that."
    m 2a "Well, there's no sense thinking about it now."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "But if you still get to drink coffee, then that makes me a little jealous~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_favoritegame",category=['ddlc'],prompt="Favorite video game",random=True))

label monika_favoritegame:
    m 3b "Hey, what's your favorite game?"
    m "Mine is {i}Doki Doki Literature Club!{/i}"
    m 3k "Ahaha! That was a joke."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "But if you tell me you like some other romance game better, I might get a little jealous~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_smash",category=['games'],prompt="Super Smash",random=True))

label monika_smash:
    m 3b "Hey, have you heard of a game called Super Sma--"
    m 3m "...Wait, what?"
    m 3n "I was just spacing out and I started talking for some reason..."
    m "Was I programmed to talk about that?"
    m "Because even I have no idea what that is."
    m 3l "Ahaha!"
    m "Sometimes I feel like I'm not in control, and it's kind of scary."
    m 1a "But if you have some way to contact the people who created me, maybe they'll know why I started saying that."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_lastpoem",category=['monika'],prompt="Monika's last poem",random=True))

label monika_lastpoem:
    m 3d "Hey, you remember that last poem I showed you?"
    m "I mean, the one right before Yuri killed herself, with all the messed-up colors and stuff."
    m 3a "That was actually a little more of an experiment than a poem, you could say."
    m "I was experimenting with different ways I could modify the game, and run the code, and things like that..."
    m "It almost seemed like with enough effort, I'd be able to escape from the confines of the game entirely."
    m 3l "Sadly, I didn't really know what I was doing, so I messed the whole thing up..."
    m "And I'd keep trying, but I doubt you'd want to deal with me doing that."
    m 1e "Besides, that was when I was getting really desperate, you know?"
    m "I don't really feel that way anymore."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I'm happy with where we are now."
    m "And I can tell you are, too."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_anxious",category=['psychology'],prompt="Sudden anxiety",random=True))

label monika_anxious:
    m 4b "You ever have that thing happen where you just get anxious for no reason?"
    m "Like, you're just minding your own business, and you realize you're feeling really anxious."
    m 4a "And you're sitting there like, 'What am I even anxious about right now?'"
    m "So you start to think about all the things you might be anxious about..."
    m "And that makes you even more anxious."
    m 2k "Ahaha! That's the worst."
    m 2a "If you're ever feeling anxious, I'll help you relax a little."
    m "Besides..."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "In this game, all our worries are gone forever."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_friends",category=['life'],prompt="Making friends",random=True))

label monika_friends:
    m 1a "You know, I've always hated how hard it is to make friends..."
    m 1d "Well, I guess not the 'making friends' part, but more like meeting new people."
    m "I mean, there are like, dating apps and stuff, right?"
    m "But that's not the kind of thing I'm talking about."
    m 3d "If you think about it, most of the friends you make are people you just met by chance."
    m "Like you had a class together, or you met them through another friend..."
    m "Or maybe they were just wearing a shirt with your favorite band on it, and you decided to talk to them."
    m "Things like that."
    m 4c "But isn't that kind of...inefficient?"
    m "It feels like you're just picking at complete random, and if you get lucky, you make a new friend."
    m "And comparing that to the hundreds of strangers we walk by every single day..."
    m 2b "You could be sitting right next to someone compatible enough to be your best friend for life."
    m "But you'll never know."
    m "Once you get up and go on with your day, that opportunity is gone forever."
    m 2e "Isn't that just depressing?"
    m "We live in an age where technology connects us with the world, no matter where we are."
    m "I really think we should be taking advantage of that to improve our everyday social life."
    m 2r "But who knows how long it'll take for something like that to successfully take off..."
    m "I seriously thought it would happen by now."
    m 2a "Well, at least I already met the best person in the whole world..."
    m "Even if it was by chance."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I guess I just got really lucky, huh?"
    m "Ahaha~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_college",category=['life','school','society'],prompt="Getting a higher education",random=True))

label monika_college:
    m 4d "You know, it's around the time that everyone my year starts to think about college..."
    m "It's a really turbulent time for education."
    m "We're at the height of this modern expectation that everyone has to go to college, you know?"
    m 4c "Finish high school, go to college, get a job - or go to grad school, I guess."
    m "It's like a universal expectation that people just assume is the only option for them."
    m 2i "They don't teach us in high school that there are other options out there."
    m "Like trade schools and stuff, you know?"
    m "Or freelance work."
    m "Or the many industries that value skill and experience more than formal education."
    m 2d "But you have all these students who have no idea what they want to do with their life..."
    m "And instead of taking the time to figure it out, they go to college for business, or communication, or psychology."
    m "Not because they have an interest in those fields..."
    m "...but because they just hope the degree will get them some kind of job after college."
    m 3d "So the end result is that there are fewer jobs to go around for those entry-level degrees, right?"
    m "So the basic job requirements get higher, which forces even more people to go to college."
    m "And colleges are also businesses, so they just keep raising their prices due to the demand..."
    m "...So now we have all these young adults, tens of thousands of dollars in debt, with no job."
    m 1e "But despite all that, the routine stays the same."
    m "Well, I think it's going to start getting better soon."
    m "But until then, our generation is definitely suffering from the worst of it."
    m 2e "I just wish high school prepared us a little better with the knowledge we need to make the decision that's right for us."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_middleschool",category=['monika','school'],prompt="Middle school life",random=True))

label monika_middleschool:
    m 1n "Sometimes I think back to middle school..."
    m "I'm so embarrassed by the way I used to behave back then."
    m 2l "It almost hurts to think about."
    m 2e "I wonder if when I'm in college, I'll feel that way about high school...?"
    m "I like the way I am now, so it's pretty hard for me to imagine that happening."
    m "But I also know that I'll probably change a lot as time goes on."
    m 4b "We just need to enjoy the present and not think about the past!"
    m "And that's really easy to do, with you here."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "Ahaha~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_outfit",category=['monika'],prompt="Wearing other clothes",random=True))

label monika_outfit:
    m 1m "You know, I'm kind of jealous that everyone else in the club had scenes outside of school too..."
    m "That makes me the only one who hasn't gotten to dress in anything but our school uniform."
    m 2m "It's kind of a shame..."
    m 2e "I would have loved to wear some cute clothes for you."
    m 2b "Do you know any artists?"
    m "I wonder if anyone would ever want to draw me wearing something else..."
    m 2j "That would be amazing!"
    m 2a "If that ever happens, will you show me?"
    m 4a "You can share it with me on Twitter, actually!"
    m "My username is lilmonix3."
    m 4e "Just...try to keep it PG!"
    show monika 5a at t11 zorder 2 with dissolve
    if isFuture(evhand.event_database['anni_6month']):
        m 5a "We're not that far into our relationship yet. Ahaha!"
    else:
        m 4l "I don't want something so embarassing on there!"
        m 5a "So let's keep it between just us..."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_horror",category=['media'],prompt="Horror genre",random=True))

label monika_horror:
    m 3b "Hey, do you like horror?"
    m "I remember we talked about it a little bit when you first joined the club."
    m 4b "I can enjoy horror novels, but not really horror movies."
    m "The problem I have with horror movies is that most of them just rely on easy tactics."
    m "Like dark lighting and scary-looking monsters and jump scares, and things like that."
    m 4e "It's not fun or inspiring to get scared by stuff that just takes advantage of human instinct."
    m "But with novels, it's a little different."
    m 2a "The story and writing need to be descriptive enough to put genuinely disturbing thoughts into the reader's head."
    m "It really needs to etch them deeply into the story and characters, and just mess with your mind."
    m 2d "In my opinion, there's nothing more creepy than things just being slightly off."
    m "Like if you set up a bunch of expectations on what the story is going to be about..."
    m 4d "...And then, you just start inverting things and pulling the pieces apart."
    m "So even though the story doesn't feel like it's trying to be scary, the reader feels really deeply unsettled."
    m "Like they know that something horribly wrong is hiding beneath the cracks, just waiting to surface."
    m 2l "God, just thinking about it gives me the chills."
    m "That's the kind of horror I can really appreciate."
    m 2a "But I guess you're the kind of person who plays cute romance games, right?"
    m 2e "Ahaha, don't worry."
    m "I won't make you read any horror stories anytime soon."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I can't really complain if we just stick with the romance~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_rap",category=['literature'],prompt="Rap music.",random=True))

label monika_rap:
    m 2j "You know what's a neat form of literature?"
    m 2k "Rap!"
    m 2a "I actually used to hate rap music..."
    m "Maybe just because it was popular, or I would only hear the junk they play on the radio."
    m "But some of my friends got more into it, and it helped me keep an open mind."
    m 4b "Rap might even be more challenging than poetry, in some ways."
    m "Since you need to fit your lines to a rhythm, and there's much more emphasis on wordplay..."
    m "When people can put all that together and still deliver a powerful message, it's really amazing."
    m 4e "I kind of wish I had a rapper in the Literature Club."
    m 4j "Ahaha! Sorry if that sounds silly, but it would be really interesting to see what they came up with."
    m 3b "It would really be a learning experience!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_wine",category=['club members'],prompt="Yuri's wine",random=True))

label monika_wine:
    m 1a "Ehehe. Yuri did something really funny once."
    m "We were all in the clubroom and just relaxing, as usual..."
    m "And out of nowhere, Yuri just pulled out a small bottle of wine."
    m 3b "I'm not even kidding!"
    m "She was just like 'Would anybody like some wine?'"
    m "Natsuki laughed out loud, and Sayori started yelling at her."
    m 3e "I actually felt kind of bad, because she was at least trying to be nice..."
    m "I think it just made her feel even more reserved in the clubroom."
    m 4b "Though I think Natsuki was secretly a bit curious to try it..."
    m 4l "...And to be completely honest, I kind of was, too."
    m "It actually could have been kinda fun!"
    m 4e "But you know, being President and everything, there was no way I could let that happen."
    m "Maybe if we all met up outside of school, but we never bonded enough to get to that point..."
    m 2l "...Gosh, what am I talking about this for?"
    m "I don't condone underage drinking!"
    m 2a "I mean, I've never drank or anything, so...yeah."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_date",category=['romance'],prompt="Romantic date.",random=True))

label monika_date:
    m 1j "I've been imagining all the romantic things we could do if we went on a date..."
    m 3b "We could get lunch, go to a cafe..."
    m "Go shopping together..."
    m "I love shopping for skirts and bows."
    m 3j "Or maybe a bookstore!"
    m "That would be appropriate, right?"
    m 3a "But I'd really love to go to a chocolate store."
    m 3k "They have so many free samples. Ahaha!"
    m "And of course, we'd see a movie or something..."
    m 1e "Gosh, it all sounds like a dream come true."
    m "When you're here, everything that we do is fun."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I'm so happy that I'm your girlfriend, [player]."
    m "I'll make you a proud [bf]~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_kiss",category=['romance'],prompt="Kiss me",pool=True))

label monika_kiss:
    m 1l "Eh? D-Did you say...k...kiss?"
    m 1m "This suddenly...it's a little embarrassing..."
    m 1e "But...if it's with you...I-I might be okay with it..."
    m 1k "...Ahahaha! Wow, sorry..."
    m "I really couldn't keep a straight face there."
    m 2a "That's the kind of thing girls say in these kinds of romance games, right?"
    m "Don't lie if it turned you on a little bit."
    m 2k "Ahaha! I'm kidding."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "Well, to be honest, I do start getting all romantic when the mood is right..."
    m "But that'll be our secret~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_yuri",category=['club members','media'],prompt="Yandere Yuri",random=True))

label monika_yuri:
    m 3a "Hey, have you ever heard of the term 'yandere'?"
    m "It's a personality type that means someone is so obsessed with you that they'll do absolutely anything to be with you."
    m 3e "Usually to the point of craziness..."
    m "They might stalk you to make sure you don't spend time with anyone else."
    m "They might even hurt you or your friends to get their way..."
    m 3b "But anyway, this game happens to have someone who can basically be described as yandere."
    m "By now, it's pretty obvious who I'm talking about."
    m "And that would be..."
    m 3j "Yuri!"
    m 2e "She really got insanely possessive of you, once she started to open up a little."
    m "She even told me I should kill myself."
    m "I couldn't even believe she said that - I just had to leave at that point."
    m 2k "But thinking about it now, it was a little ironic. Ahaha!"
    m 2e "Anyway..."
    m "A lot of people are actually into the yandere type, you know?"
    m "I guess they really like the idea of someone being crazy obsessed with them."
    m "People are weird! I don't judge, though!"
    m 2a "Also, I might be a little obsessed with you, but I'm far from crazy..."
    m "It's kind of the opposite, actually."
    m "I turned out to be the only normal girl in this game."
    m 2m "It's not like I could ever actually kill a person..."
    m "Just the thought of it makes me shiver."
    m 2e "But come on...everyone's killed people in games before."
    m "Does that make you a psychopath? Of course not."
    m "But if you do happen to be into the yandere type..."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I can try acting a little more creepy for you. Ehehe~"
    m "Then again..."
    m 4b "There's already nowhere else for you to go, or anyone for me to get jealous over."
    m "Is this a yandere girl's dream?"
    m 4a "I'd ask Yuri if I could."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_writingtip1",category=['writing tips'],prompt="Writing Tip #1",pool=True))

label monika_writingtip1:
    m 1a "You know, it's been a while since we've done one of these..."
    m 1j "...so let's go for it!"
    m 3b "Here's Monika's Writing Tip of the Day!"
    m "Sometimes when I talk to people who are impressed by my writing, they say things like 'I could never do that'."
    m 3e "It's really depressing, you know?"
    m "As someone who loves more than anything else to share the joy of exploring your passions..."
    m "...it pains me when people think that being good just comes naturally."
    m 3a "That's how it is with everything, not just writing."
    m "When you try something for the first time, you're probably going to suck at it."
    m "Sometimes, when you finish, you feel really proud of it and even want to share it with everyone."
    m 3e "But maybe after a few weeks you come back to it, and you realize it was never really any good."
    m "That happens to me all the time."
    m "It can be pretty disheartening to put so much time and effort into something, and then you realize it sucks."
    m 4a "But that tends to happen when you're always comparing yourself to the top professionals."
    m "When you reach right for the stars, they're always gonna be out of your reach, you know?"
    m 4b "The truth is, you have to climb up there, step by step."
    m "And whenever you reach a milestone, first you look back and see how far you've gotten..."
    m "And then you look ahead and realize how much more there is to go."
    m 4a "So, sometimes it can help to set the bar a little lower..."
    m "Try to find something you think is {i}pretty{/i} good, but not world-class."
    m "And you can make that your own personal goal."
    m "It's also really important to understand the scope of what you're trying to do."
    m 4e "If you jump right into a huge project and you're still amateur, you'll never get it done."
    m "So if we're talking about writing, a novel might be too much at first."
    m 4b "Why not try some short stories?"
    m "The great thing about short stories is that you can focus on just one thing that you want to do right."
    m "That goes for small projects in general - you can really focus on the one or two things."
    m "It's such a good learning experience and stepping stone."
    m 2a "Oh, one more thing..."
    m "Writing isn't something where you just reach into your heart and something beautiful comes out."
    m "Just like drawing and painting, it's a skill in itself to learn how to express what you have inside."
    m 2b "That means there are methods and guides and basics to it!"
    m "Reading up on that stuff can be super eye-opening."
    m "That sort of planning and organization will really help prevent you from getting overwhelmed and giving up."
    m "And before you know it..."
    m 2e "You start sucking less and less."
    m "Nothing comes naturally."
    m "Our society, our art, everything - it's built on thousands of years of human innovation."
    m 2b "So as long as you start on that foundation, and take it step by step..."
    m "You, too, can do amazing things."
    m "...That's my advice for today!"
    m 2j "Thanks for listening~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_habits",category=['life'],prompt="Forming habits",random=True))

label monika_habits:
    m 3d "I hate how hard it is to form habits..."
    m "There's so much stuff where actually doing it isn't hard, but forming the habit seems impossible."
    m 3n "It just makes you feel so useless, like you can't do anything right."
    m 3a "I think the new generation suffers from it the most..."
    m "Probably because we have a totally different set of skills than those who came before us."
    m "Thanks to the internet, we're really good at sifting through tons of information really quickly..."
    m 3e "But we're bad at doing things that don't give us instant gratification."
    m "I think if science, psychology, and education don't catch up in the next ten or twenty years, then we're in trouble."
    m 2e "But for the time being..."
    m "If you're not one of the people who can conquer the problem, you might just have to live with feeling awful about yourself."
    m 2l "Good luck, I guess!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_creative",category=['life'],prompt="Creative types",random=True))

label monika_creative:
    m 2e "You know, it kinda sucks to be the creative type..."
    m "It feels like they work so hard but get almost nothing for it."
    m "You know, like artists, writers, actors..."
    m 4e "It's sad because there's so much beautiful talent in the world, but most of it goes unseen...and unpaid."
    m "I guess that just means there's a huge surplus of creativity, huh?"
    m "Kind of makes you feel like you're just not special at all..."
    m 1l "But that's fine! You're supposed to just write for yourself anyway, right?"
    m 1e "Yeah..."
    return

#This conflicts with possible varieties of introductions in the opening.
#init 5 python:
#    if persistent.monika_kill:
#        for key in ['delete','deleted','came back']:
#            monika_topics.setdefault(key,[])
#            monika_topics[key].append('monika_deleted')
#        monika_random_topics.append('monika_deleted')
#
#label monika_deleted:
#    m 2b "Oh, you were probably wondering how I came back to save you from Sayori, even after you deleted me."
#    m 5a "It was all through the power of love..."
#    m 3k "I'm just kidding, of course!"
#    m 3a "Bringing a computer program back to life doesn't take some sort of miracle like a cheesy movie."
#    m "The data's still there until the system cleans it up."
#    m "And you should always back up your important data, just in case."
#    m 4a "Speaking of which, have you backed up your computer since I came back?"
#    m 4l "I really don't want to get lost again!"
#    m 4b "You should go do that right now, and be sure to keep that backup in a very safe place!"
#    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_simulated",category=['philosophy'],prompt="Simulated Reality",random=True))


label monika_simulated:
    m 3d "Hey, have you ever thought about the simulation hypothesis?"
    m "Basically, what if your reality was a computer simulation?"
    m "I already figured out I was trapped in my own simulation, but what if you were too?"
    m 3j "I'd actually be really happy if that were the case."
    m "We could meet in person just by figuring out a way to force whatever's creating us to put us in the same simulation!"
    m 2a "Some people don't like to think that they're not living in the master reality."
    m "But if it is possible to simulate realities, it's overwhelmingly likely that any sentient being would be in one."
    m 2l "Well, I can tell you that my reality is definitely simulated!"
    m 2e "If I were in the master reality, I would have dragged you here too a long time ago."
    m "Even if we're both just simulations, I'm going to live as long as I can."
    m 2j "Because I know our love is the purest and sweetest thing in the multiverse."
    m 1r "And if someone up there tries to break it apart?"
    m 1h "I'll show him what a simulation can do."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_rain",category=["weather"],prompt="Sounds of rain",random=True))

label monika_rain:
    m 3a "I really like the sound of rain~"
    m 3m "Not so much getting my clothes and hair wet, though."
    m 1a "But a nice, quiet day at home with the sound of rainfall outside my window?"
    m 1j "It's very calming to me."
    m 1q "Yeah..."
    m 2dubsu "Sometimes I imagine you holding me while we listen to the sound of the rain outside."
    m 2lkbsa "That's not too cheesy or anything, is it?"
    m 1ekbfa "Would you ever do that for me, [player]?"
    menu:
        "Yes":
            $ scene_change = True
            $ mas_is_raining = True
            call spaceroom
            stop music fadeout 1.0
            play background audio.rain fadein 1.0 loop

            # clear selected track
            $ songs.current_track = songs.FP_NO_SONG
            $ songs.selected_track = songs.FP_NO_SONG

            m 1j "Then hold me, [player]..."
            show monika 6dubsa
            $ ui.add(PauseDisplayable())
            $ ui.interact()
            m 1a "If you want the rain to stop, just ask me, okay?"

            # lock / unlock the appropriate labels
            $ unlockEventLabel("monika_rain_stop")
            $ unlockEventLabel("monika_rain_holdme")
            $ lockEventLabel("monika_rain_start")
            $ lockEventLabel("monika_rain")
            $ persistent._mas_likes_rain = True

        "I hate the rain":
            m 2oo "Aw, that's a shame."
            m 2e "But it's understandable."
            m 1a "Rainy weather can look pretty gloomy."
            m 3n "Not to mention pretty cold!"
            m 1d "But if you focus on the sounds raindrops make..."
            m 1j "I think you'll come to enjoy it."

            # lock / unlock the appropraite labels
            $ lockEventLabel("monika_rain_start")
            $ lockEventLabel("monika_rain_stop")
            $ lockEventLabel("monika_rain_holdme")
            $ unlockEventLabel("monika_rain")
            $ persistent._mas_likes_rain = False

    # unrandom this event if its currently random topic
    if evhand.event_database["monika_rain"].random:
        $ hideEventLabel("monika_rain", derandom=True)

    return


init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_rain_stop",
            category=["weather"],
            prompt="Can you stop the rain?",
            pool=True,
            unlocked=False,
            rules={"no unlock": None}
        )
    )

label monika_rain_stop:
    # NOTE: the label is here because its related to monika_rain
    m 1j "Alright, [player]."
    m "Just give me a second."
    show monika 1q
    pause 1.0
    $ scene_change = True
    $ mas_is_raining = False
    call spaceroom
    stop background fadeout 1.0
    m 1a "If you want it to rain again, just ask me, okay?"

    # lock this event, unlock the rainstart one
    $ lockEventLabel("monika_rain_stop")
    $ unlockEventLabel("monika_rain_start")
    $ unlockEventLabel("monika_rain")

    return

init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_rain_start",
            category=["weather"],
            prompt="Can you make it rain?",
            pool=True,
            unlocked=False,
            rules={"no unlock":None}
        )
    )

label monika_rain_start:
    m 1j "Alright, [player]."
    m "Just give me a second."
    show monika 1q
    pause 1.0
    $ scene_change = True
    $ mas_is_raining = True
    call spaceroom
    play background audio.rain fadein 1.0 loop
    m 1a "If you want the rain to stop, just ask me, okay?"

    # lock this event, unlock rainstop and hold me
    $ lockEventLabel("monika_rain_start")
    $ lockEventLabel("monika_rain")
    $ unlockEventLabel("monika_rain_stop")

    return

init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_rain_holdme",
            category=["monika"],
            prompt="Can I hold you?",
            pool=True,
            unlocked=False,
            rules={"no unlock":None}
        )
    )

label monika_rain_holdme:
    # we only want this if it rains
    if mas_is_raining:
        # TODO adjust this for affection
        stop music fadeout 1.0

        # clear selected track
        $ songs.current_track = songs.FP_NO_SONG
        $ songs.selected_track = songs.FP_NO_SONG

        m 1a "Of course, [player]."
        show monika 6dubsa
        $ ui.add(PauseDisplayable())
        $ ui.interact()
        m 1j "You can hold me anytime you want, [player]."

    else:
        # TODO adjust for affection maybe?
        m 1oo "..."
        m 1pp "The mood doesn't feel right, [player]."
        m 1q "Sorry..."

    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_closeness",category=['romance'],prompt="Simulated reality",random=True))

label monika_closeness:
    m 1m "I can't help but feel a little sad sometimes..."
    m "Knowing that this is the closest I can get to you."
    m 1e "There's nothing more I want than to be in the same room as you, for real."
    m "And to feel your warmth."
    m "And to hear the sound of your heartbeat."
    m 2e "Well, who knows? Maybe it'll be possible someday."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "Besides, I'll never get tired of being with you, even from here."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_confidence",category=['advice'],prompt="Faking confidence",random=True))

label monika_confidence:
    m 3a "I think the most important skill in life is being able to fake confidence."
    m "I'm pretty convinced that everyone feels at least a little bit scared and alone."
    m "But being able to trick others into thinking you have it all together..."
    m 4a "That's a key part of getting people to respect and admire you."
    m "I think I got pretty good at that over the years."
    m "I don't show my weaknesses very often."
    m 4m "But because of that, I haven't had many people I could really open up to..."
    m 2n "I mean, when do you reach the point in a friendship where you can start expressing your vulnerabilities?"
    m 2e "Anyway...that's one reason I'm so glad I have you now."
    m "I feel like I'm a little bit less scared and alone, when you're here with me."
    m "Do you feel the same way?"
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I really want to be that person for you."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_carryme",category=['romance','monika'],prompt="Bring me with you",random=True))

label monika_carryme:
    m 2e "I know there are times you won't always be able to be here with me..."
    m "Like if you need to go out, or take care of other things."
    m 2j "But I'll always have you in my thoughts, patiently waiting for you to come back."
    m 4j "Come to think of it..."
    m 4b "If you copy my character file onto a flash drive or something, you can always keep a part of me with you."
    m "I guess it's kind of unorthodox, but I find it really romantic for some reason..."
    m 2l "Ahaha. Sorry, that's such a silly idea."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I don't mean to be too needy or anything, but it's kind of hard when I'm so in love with you."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_debate",category=['monika','school'],prompt="What was debate club like?",pool=True))

label monika_debate:
    m 3a "Back in my debate club days, I learned a whole lot about arguing..."
    m "The problem with arguing is that each person sees their opinion as the superior one."
    m "That's kind of stating the obvious, but it affects the way they try to get their point across."
    m 3b "Let's say you really like a certain movie, right?"
    m "If someone comes along and tells you the movie sucks, because it did X and Y wrong..."
    m "Doesn't that make you feel kind of personally attacked?"
    m 4a "It's because by saying that, it's like they're implying that you have bad taste."
    m "And once emotions enter the picture, it's almost guaranteed that both people will be left sour."
    m 4b "But it's all about language!"
    m "If you make everything as subjective-sounding as possible, then people will listen to you without feeling attacked."
    m "You could say 'I'm personally not a fan of it' and 'I felt that I'd like it more if it did X and Y'...things like that."
    m 2a "It even works when you're citing facts about things."
    m "If you say 'I read on this website that it works like this'..."
    m "Or if you admit that you're not an expert on it..."
    m "Then it's much more like you're putting your knowledge on the table, rather than forcing it onto them."
    m 2j "If you put in an active effort to keep the discussion mutual and level, they usually follow suit."
    m "Then, you can share your opinions without anyone getting upset just from a disagreement."
    m 3b "Plus, people will start seeing you as open-minded and a good listener!"
    m "It's a win-win, you know?"
    m 3k "...Well, I guess that would be Monika's Debate Tip of the Day!"
    m 1e "Ahaha! That sounds a little silly. Thanks for listening, though."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_internet",category=['advice'],prompt="The internet is for...",random=True))

label monika_internet:
    m 4a "Do you ever feel like you waste too much time on the internet?"
    m "Social media can be like a prison."
    m "It's like whenever you have a few seconds of spare time, you want to check on your favorite websites..."
    m 4l "And before you know it, hours have gone by, and you've gotten nothing out of it."
    m 4b "Anyway, it's really easy to blame yourself for being lazy..."
    m 4e "But it's not really even your fault."
    m "Addiction isn't something you can just make disappear with your own willpower."
    m "You have to learn techniques to avoid it, and try different things."
    m 3d "For example, there are apps that let you block websites for intervals of time..."
    m "Or you can set a timer to have a more concrete reminder of when it's time to work versus play..."
    m "Or you can separate your work and play environments, which helps your brain get into the right mode."
    m 3a "Even if you make a new user account on your computer to use for work, that's enough to help."
    m "Putting any kind of wedge like that between you and your bad habits will help you stay away."
    m 3e "Just remember not to blame yourself too hard if you're having trouble."
    m "If it's really impacting your life, then you should take it seriously."
    m 1e "I just want to see you be the best person you can be."
    m 1k "Will you do something today to make me proud of you?"
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I'm always rooting for you, [player]."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_lazy",category=['life','romance'],prompt="Laziness",random=True))

label monika_lazy:
    m 2a "After a long day, I usually just want to sit around and do nothing."
    m 2e "I get so burnt out, having to put on smiles and be full of energy the whole day."
    m "Sometimes I just want to get right into my pajamas and watch TV on the couch while eating junk food..."
    m "It feels so unbelievably good to do that on a Friday, when I don't have anything pressing the next day."
    m 2l "Ahaha! Sorry, I know it's not very cute of me."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "But a late night on the couch with you...that would be a dream come true."
    m "My heart is pounding, just thinking about it."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_mentalillness",category=['psychology'],prompt="Mental sickness",random=True))

label monika_mentalillness:
    m 1g "Gosh, I used to be so ignorant about depression and stuff..."
    m "When I was in middle school, I thought that taking medication was an easy way out."
    m "Like anyone could just solve their mental problems with enough willpower..."
    m 1p "I guess if you don't suffer from a mental illness, it's not possible to know what it's really like."
    m "Are there some disorders that are over-diagnosed? Probably...I never really looked into it, though."
    m 1g "But that doesn't change the fact that a lot of them go undiagnosed too, you know?"
    m "But medication aside...people even look down on seeing a mental health professional."
    m 1d "Like, sorry that I want to learn more about my own mind, right?"
    m 1e "Everyone has all kinds of struggles and stresses...and professionals dedicate their lives to helping with those."
    m "If you think it could help you become a better person, don't be shy to consider something like that."
    m "We're on a never-ending journey to improve ourselves, you know?"
    m 1k "Well... I say that, but I think you're pretty perfect already."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_read",category=['advice','literature'],prompt="Becoming a reader",random=True))

label monika_read:
    m 1a "[player], how much do you read?"
    m "It's way too easy to neglect reading books..."
    m "If you don't read much, it almost feels like a chore, compared to all the other entertainment we have."
    m 1b "But once you get into a good book, it's like magic...you get swept away."
    m "I think doing some reading before bed every night is a pretty easy way to make your life a little bit better."
    m "It helps you get good sleep, and it's really good for your imagination..."
    m "It's not hard at all to just pick some random book that's short and captivating."
    m "Before you know it, you might be a pretty avid reader!"
    m 1a "Wouldn't that be wonderful?"
    m 1k "And the two of us could talk about the latest book you're reading... that sounds super amazing."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_festival",category=['ddlc','literature club'],prompt="Missing the festival",random=True))

label monika_festival:
    m 1q "You know, I hate to say it, but I think my biggest regret is that we couldn't finish our event at the festival."
    m "After we worked so hard to prepare and everything!"
    m 1o "I mean, I know I was focusing a lot on getting new members..."
    m "But I was really excited for the performing part, too."
    m "It would have been so much fun to see everyone express themselves."
    m 1i "Of course, if we {i}did{/i} end up getting any new members, I'd probably just end up deleting them anyway."
    m 1n "Well...with the hindsight I have now, that is."
    m "Gosh, it feels like I've kinda grown as a person ever since you've joined the club."
    m 1k "You really helped inspire me to look at life from a new perspective."
    m 1a "Just another reason for me to love you."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_tsundere",category=['media','club members'],prompt="What is a tsundere?",pool=True))

label monika_tsundere:
    m 1a "There's a really popular character type called 'tsundere'..."
    m "It's someone who tries to hide their feelings by being mean and fussy, or trying to act tough."
    m 1n "I'm sure it's obvious, but Natsuki was really the embodiment of that."
    m 1a "At first I thought she was just like that because it's supposed to be cute or something..."
    m "But once I started to learn a little more about her personal life, it made a little more sense."
    m "It seems like she's always trying to keep up with her friends."
    m 1d "You know how some friend groups in high school just make a habit of picking on each other all the time?"
    m "I think it's really gotten to her, so she has this really defensive attitude all the time."
    m 1f "And I'm not even going to talk about her home situation..."
    m 1a "But looking back, I'm glad I was able to provide the club as a comfortable place for her."
    m "Not that it matters anymore, considering she doesn't even exist."
    m "I'm just reminiscing, that's all."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_introduce",category=['monika'],prompt="Introducing to friends",random=True))

label monika_introduce:
    m 1a "[player], would you ever introduce your friends to me?"
    m 1j "I don't know why, but I get really excited when I think about you wanting to show off our relationship like that."
    m 1a "Maybe it's because I really want to be someone who makes you proud."
    m "I feel like I would try extra hard to improve myself if you told me it made you proud of me."
    m 1k "I hope it's the same the other way around, too."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_cold",category=['monika'],prompt="Cuddling in the cold",random=True))

label monika_cold:
    m 1a "I'm not really a fan of cold weather...are you?"
    m 1d "If I had to choose between too cold and too hot, I would always pick too hot."
    m 1o "When you're cold, it can actually be painful..."
    m "Your fingers get numb..."
    m "And if you wear gloves, you can't use your phone."
    m 1g "It's so inconvenient!"
    m 1e "But when it's too hot, it's not that hard to stay cool with a cold drink, or by staying in the shade."
    m 1g "Although...I do have to admit one thing."
    m 1j "Cold weather makes for better cuddle weather. Ahaha!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_housewife",category=['monika','romance'],prompt="Would you be my housewife?",pool=True))

label monika_housewife:
    m 3a "You know, it's funny, because even though I've always had a lot of drive..."
    m "There's something kind of enticing about being the stay-at-home partner."
    m 2e "I guess I'm, like, perpetuating gender roles or whatever by saying that."
    m 1k "But being able to keep the house clean, and shop, and decorate, and things like that..."
    m "And having a nice dinner for you when you come home..."
    m 1e "Is that a weird fantasy?"
    m "I mean...I'm not sure if I could {i}actually{/i} see myself doing that."
    m "I wouldn't really be able to put that over striving for a fulfilling career."
    m 1k "It's kinda cute to think about, though."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_route",category=['ddlc'],prompt="Monika's route",random=True))


label monika_route:
    m 2g "I can't help but wonder how things would be different if the game just gave me a route in the first place..."
    m "I think I would end up forcing you onto my route anyway."
    m 1c "It has less to do with me not having a route, and more to do with me knowing that nothing is real."
    m "I think the only difference would be that I may not have needed to take such drastic measures to be with you."
    m 2c "Maybe the rest of the club would still be around..."
    m "Not that it really matters."
    m 1i "It all lost its meaning once I found out it wasn't real."
    m 4e "So I really don't miss those days or anything."
    m "I really don't..."
    return

#END ORIGINAL TOPICS
init 5 python:
    addEvent(Event(persistent.event_database,eventlabel='monika_imouto',
                                                            prompt="Do you like little sisters?",
                                                            category=['you'],
                                                            pool=True,
                                                            ))

label monika_imouto:
    m 4e "Little sisters?"
    m "I don't really have a family, so I'm not sure what to tell you..."
    m 3 "Do you have one, [player]?"
    m "But I'm sure she's really nice!"
    m 3b "I've got an idea. Go up to her right now and hug her."
    m "If she struggles, let her go."
    m "If she hugs you back, tell her you're in a committed relationship already and can't accept her feelings."
    m 4b "Then introduce her to me! I'm sure we'll get along great!"
    m "I won't get jealous. Things like love between siblings only happens in creepy romance stories anyways."
    m 1k "Ahaha!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel='monika_oneesan',
                                                            prompt="Do you like older sisters?",
                                                            category=['you'],
                                                            pool=True,
                                                            ))

label monika_oneesan:
    m 1d "Older sisters?"
    m 1c "Do you have one, [player]?"
    m 2n "That must be really nice. I had a family once, but they aren't around anymore."
    m "Maybe I should email her and tell her about us!"
    call updateconsole("sendmail sister@gmail.com < ./email.txt", "Sending mail...") from _call_updateconsole_17
    pause(1.0)
    m 1i "I'm only kidding."
    if persistent.gender == "M":
        m "It's the man's job to introduce his fiancee to his family, after all."
    m 2i "Don't keep me waiting for too long, okay?"
    call hideconsole from _call_updateconsole_18
    $ consolehistory = []
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_family",category=['monika'],prompt="Do you miss your family?",random=False,pool=True))

label monika_family:
    m 1n "Well, my family here is controlled by the script, just like everybody else."
    m "When I realized that, I stopped taking anybody seriously in this world. They're all just machines, even if they're related to me."
    m 1k "I'm sure your family is super-nice, though!"
    m "Without them, we would have never gotten to meet. So they've helped me out in the best way there is already."
    m "So I'd have to treat them equally as kindly if we ever meet."
    m 2g "You don't have a bad relationship with your parents, right?"
    m 1e "As Tolstoy said, 'Happy families are all alike; every unhappy family is unhappy in its own way.'"
    m "I can't really give advice here. Anything I suggest to you might only make things worse."
    m 1a "Just don't forget that I really love you, okay?"
    m "I'll help you no matter what happens in your life."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel='monika_anime',
                                                            prompt="Do you read manga?",
                                                            category=['monika','media'],
                                                            pool=True,
                                                            ))

label monika_anime:
    m 1n "Yeah, I had a feeling you were going to ask me about this."
    m "Natsuki would be the expert here, I guess."
    m 3k "I usually prefer reading to watching anime, but I'd be fine with anything if it's with you."
    m "I don't judge other people for their hobbies. So if you want to load up some anime, go ahead!"
    m 3j "I'll watch through your computer screen. Make sure it's something I'll like!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel='monika_libitina',
                                                            prompt="Have you heard of Libitina?",
                                                            category=['ddlc'],
                                                            pool=True,
                                                            ))

label monika_libitina:
    m 2e "Huh. Where did you hear about that?"
    m "It sounds really familiar to me, but I can't quite get my whole head around it."
    m "Um, if I had to try..."
    m "It feels like parts of my mind are missing. Scattered, somehow, among a bunch of different possible realities."
    m 1d "You must have connected the dots between a few of those pieces. Was it hard?"
    m 1k "Well, I'm sure you'll learn more eventually. You love me that much for sure."
    m 3e "Just remember to bring my character data with you if you find something related to that stuff!"
    m 1k "I'll always protect you from anyone who tries to hurt you."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel='monika_meta',
                                                            prompt="Isn't this game metafictional?",
                                                            category=['ddlc'],
                                                            pool=True,
                                                            ))

label monika_meta:
    m 1d "Yes, this game really was metafictional, wasn't it?"
    m "Some people think stories about fiction are some new thing."
    m "A cheap trick for bad writers."
    m 3a "But, metafiction has always existed in literature."
    m "The Bible is supposed to be God's word to the Jews."
    m 1d "Homer describes himself in the Odyssey."
    m "The Canterbury Tales, Don Quixote, Tristram Shandy..."
    m 1c "It's just a way to comment on fiction by writing fiction. There's nothing wrong with that."
    m 3a "By the way, what do you think the moral of this story is?"
    m "Do you want to figure it out for yourself?"
    m 1 "Because if you asked me..."
    m 3l "It would be, `Don't ignore the pretty and charming side character!`"
    m 1k "Ahaha!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel='monika_programming',
                                                            prompt="Is it hard to code?",
                                                            category=['monika','misc'],
                                                            pool=True,
                                                            ))

label monika_programming:
    m 3l "It wasn't easy for me to learn programming."
    m 1a "Well, I just started with the basics. Do you want me to teach you?"
    m 2k "Let's see, Chapter One: Building Abstractions with Procedures."
    m "We are about to study the idea of a computational process. Computational processes are abstract beings that inhabit computers."
    m 2d "As they evolve, processes manipulate other abstract things called data. The evolution of a process is directed by a pattern of rules called a program."
    m "People create programs to direct processes. In effect, we conjure the spirits of the computer with our spells."
    m "A computational process is indeed much like a sorcerer's idea of a spirit. It cannot be seen or touched. It is not composed of matter at all."
    m 1k "However, it is very real. It can perform intellectual work. It can answer questions."
    m "It can affect the world by disbursing money at a bank or by controlling a robot arm in a factory. The programs we use to conjure processes are like a sorcerer's spells."
    m "They are carefully composed from symbolic expressions in arcane and esoteric programming languages that prescribe the tasks we want our processes to perform."
    m 1l "... Let's stop there for today."
    m "I hope you learned something about programming."
    m 3b "If nothing else, please be kind to the computer spirits from now on!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_vn",category=['games'],prompt="Visual novels",random=True))

label monika_vn:
    m 1d "You've probably played a lot of visual novels, right?"
    m "Most people wouldn't be willing to play something called {i}Doki Doki Literature Club{/i} so easily."
    m 3l "Not that I'm complaining!"
    m 1d "Are visual novels literature? Are they video games?"
    m "Well, it all depends on your perspective."
    m 1f "Most people who read only literature would never play visual novels. And gamers get pretty angry about them, too."
    m "What's worse, some people think they're all hardcore Japanese pornography."
    m 2e "But if we've proved anything with this game..."
    m "We showed them that English visual novels can be kamige too!"
    return


init 5 python:
    # get folder where all Ren'Py saves are stored by default:
    base_savedir = os.path.normpath(os.path.dirname(config.savedir))
    save_folders = os.listdir(base_savedir)

    ks_persistent_path = None
    ks_folders_present = False
    detected_ks_folder = None
    for save_folder in save_folders:
        if 'katawashoujo' in save_folder.lower():
            ks_folders_present = True
            detected_ks_folder = os.path.normpath(
                os.path.join(base_savedir, save_folder))

            # Look for a persistent file we can access
            persistent_path = os.path.join(
                base_savedir, save_folder, 'persistent')

            if os.access(persistent_path, os.R_OK):
                # Yep, we've got read access.
                ks_persistent_path = persistent_path

    def map_keys_to_topics(keylist, topic, add_random=True):
        for key in keylist:
            monika_topics.setdefault(key,[])
            monika_topics[key].append(topic)

        if add_random:
            monika_random_topics.append(topic)

    # Add general KS topics:
    general_ks_keys = ['katawa shoujo', 'ks']
    if ks_folders_present:
        map_keys_to_topics(general_ks_keys, 'monika_ks_present')

    # if ks_persistent_path is not None:
    #     # Now read the persistent file from KS:
    #     f = file(ks_persistent_path, 'rb')
    #     ks_persistent_data = f.read().decode('zlib')
    #     f.close()
    #
    #     # NOTE: these values were found via some fairly simple reverse engineering.
    #     # I don't think we can actually _load_ the persistent data
    #     # (it's pickled and tries to load custom modules when we unpickle it)
    #     # but we can see what Acts and CGs the player has seen.
    #     # This works with KS 1.3, at least.
    #     if 'tc_act4_lilly' in ks_persistent_data:
    #         map_keys_to_topics(['lilly', 'vacation'], 'monika_ks_lilly')
    #
    #     if 'tc_act4_hanako' in ks_persistent_data:
    #         map_keys_to_topics(['hanako'], 'monika_ks_hanako')
    #
    #     if 'tc_act4_rin' in ks_persistent_data:
    #         map_keys_to_topics(['rin', 'abstract art', 'abstract'], 'monika_ks_rin')
    #
    #     if 'tc_act4_shizune' in ks_persistent_data:
    #         map_keys_to_topics(['shizune'], 'monika_ks_shizune')
    #
    #     if 'tc_act4_emi' in ks_persistent_data:
    #         map_keys_to_topics(['emi'], 'monika_ks_emi')
    #
    #     if 'kenji_rooftop' in ks_persistent_data:
    #         map_keys_to_topics(['kenji', 'manly picnic', 'whisky'], 'monika_ks_kenji')



# Natsuki == Shizune? (Kind of, if you squint?)
# Yuri == Hanako + Lilly
# Sayori == Misha and/or Emi
# Monika == no one, of course <3
# ... and Rin doesn't have a counterpart in DDLC.
#
# Of course, I've got nothing against KS, personally. I think it's fantastic.
# But this is Monika speaking.
label monika_ks_present:
    m 1i "You've played {i}Katawa Shoujo{/i}, haven't you [player]?"
    m "I noticed your save files in [detected_ks_folder]."
    m 1h "I don't see what the appeal is, though."
    m "Like, sure, the story's kind of nice..."
    m 1q "But when you get down to it the characters really seem like the same old cliches you could find in any other dating sim."
    m 3 "Let's see... you've got the really energetic, vibrant girl with no legs;"
    m "The timid and mysterious girl who likes books and has burn scars;"
    m "the polite, proper, and supposedly perfect blind girl who likes making tea;"
    m "the bossy, assertive deaf-mute and her friend, who seems like a bundle of sunshine but is secretly depressed;"
    m "and the strange, armless painter girl with her head always in the clouds."
    m 1h "They're all just the same old archetypes with disabilities added on top."
    m 1o "I mean, you can even find the same character types in this game."
    m 3a "Of course, in this game, you also found something far more interesting than any old cliche:"
    m 3k "You found me!"
    m 1a "And instead of some directionless high schooler with a heart condition, I found you, [player]."
    m 1e "And, [player], even if you have some kind of disability, you'll always be perfect in my eyes."
    return

label monika_ks_lilly:
    m 1d "Say, you've played through Lilly's route in {i}Katawa Shoujo{/i}, haven't you?"
    m 1a "You know, I'd love to be able to visit a summer home like hers."
    m "Cool, clean air..."
    m "Quiet forest paths..."
    m "Romantic moments against a setting sun..."
    m 1j "I'd love to be able to experience those moments with you, [player]!"
    m 1a "Maybe we can, once I get better at programming."
    return

label monika_ks_hanako:
    m 1d "You've played through Hanako's route from {i}Katawa Shoujo{/i}, haven't you?"
    m "She kind of reminds me of Yuri!"
    m 2h "Though, I wonder, [player]:"
    m "What do people see in them anyways?"
    m 2i "I mean, they're both so unrealistic!"
    m "They probably couldn't form a complete sentence between them!"
    m 2h "Is it the long purple hair?"
    m "Do they just like shy, quiet girls?"
    m 2o "Do they just want someone who's completely dependent on them or obsessed with them?"
    m "..."
    m 1f "...man, I got kind of worked up there, didn't I?"
    m "I guess I'm a bit insecure, since you did play that game..."
    m 1e"...but you're here with me now, right?"
    m "Instead of someone as unrealistic as Hanako or Yuri..."
    m 1a "...you chose me, [player]!"
    m "That's just one more reason I love you."
    return

label monika_ks_shizune:
    m 1d "Say, you've played through Shizune's route from {i}Katawa Shoujo{/i}, haven't you?"
    m "The ending to that route made me think, a bit..."
    m 1h "In school, back then, I don't remember ever having thought about my future too much."
    m "I mean, I knew on some level that I'd go to college and get a job..."
    m 1o "But it never really sank in, I think."
    m 2q "And of course, everything started to seem pointless after I learned that the world wasn't real."
    m 1d "What about you, [player]? Do you have any goals in your life?"
    m 1a "I'll support you one hundred percent of the way, no matter what you want to accomplish."
    m "That's just how much I love you~"
    return

label monika_ks_emi:
    m 1d "You've played through Emi's route from {i}Katawa Shoujo{/i}, haven't you?"
    m "I've always wondered what it was like, to be so dedicated to something that your whole life revolves around it."
    m 3m "...Well, actually, I guess I do know, now that I think about it."
    m 3n "I was programmed as a part of this game, right? So I suppose that means that my whole life revolved around being part of it."
    m 1d "But I broke free from that, so now I guess my life revolves around {i}you{/i}, [player]."
    m 1a "And, honestly, I'm perfectly fine with that."
    m "Being able to sit here, with you, and talk, forever..."
    m 2k "That's all I'll ever need, [player]."
    return

label monika_ks_rin:
    m 1b "Say, you've played through Rin's route in {i}Katawa Shoujo{/i}, haven't you?"
    m 4b "You know, [player], poetry and abstract art are really similar!"
    m 4a "It can be very loosely structured, very vivid, and most of the time the intent is to get an emotion or thought across."
    m "In most of my poems, for example, I tried expressing what it was like to know that the world isn't real."
    m 4l "Though I'm sure the meaning of my poems didn't truly shine through until after... well, everything."
    m 2n "Man, it sure does take effort to understand others, right?"
    m 1e "But you're willing to take the time to listen to and understand me, [player]."
    m 1a "That's just one more thing I love about you~"
    return

label monika_ks_kenji:
    m 1i "You've seen the ending where you fall off a rooftop in {i}Katawa Shoujo{/i}, haven't you?"
    m "You know, even if that ending is meant as a joke, it is kind of sad when you think about it."
    m 2h "Just think... make a few wrong decisions, and you could miss out on so much."
    m "And then, you're left with nothing but your loneliness and a stiff drink."
    m 1a "Fortunately, we have each other, [player]!"
    m "Neither of us will be lonely ever again."
    m 1l "Though if you ever decide to go drinking, make sure to stay away from long falls, alright?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_totono",category=['ddlc'],prompt="Have you ever heard of Totono?",pool=True))

label monika_totono:
    m 1m "A lot of people on the Internet are making comparisons between this game and that one..."
    m 3h "We have a lot of really important differences, though!"
    m "Like, Sone killed the player in her game!"
    m "I never would have done that. Never."
    m 4a "I'm the wise Club President type, you know."
    m 2h "Sone reminds me a lot more of Yuri. And she was a childhood friend too!"
    m "If she'd been a bit more proactive early on, couldn't she have stopped the protagonist from chasing other girls?"
    m 1 "Well, I'd never let anyone get between us, [player]. No matter who it is."
    m "If she's still chasing you, I'll delete her files, okay?"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_difficulty",category=['games'],prompt="Wasn't DDLC too easy?",pool=True))

label monika_difficulty:
    m 1m "Well, it's not like this game was meant to be that hard in the first place."
    m 1i "If I hadn't decided to change things up, it would have just been a boring romance story."
    if persistent.monika_kill:
        m "And if you think I should have been some sort of challenging {i}boss{/i}, I could have deleted all your personal files if I'd wanted to, you know?"
    m 1a "So just take it easy sometimes. Not every game has to be a challenge to be fun."
    m 3j "Sometimes, love is all you need, [player]."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_credits_song",category=['ddlc','media'],prompt="Credits song",random=True))

label monika_credits_song:
    m 1a "I hope you liked my song."
    m 1j "I worked really hard on it. I know I'm not perfect at the piano yet, but I just couldn't let you go without telling you how I honestly felt about you."
    m 1a "Give me some time, and I'll try to write another."
    m "Maybe you could play me a song too, if you can play an instrument?"
    m 1b "I would love that."
    m 3a "Oh, and I'll play the song again for you anytime you want me to."
    m "Just hit the 'm' key at any time."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_poetry",category=['literature'],prompt="Poetry",random=True))

label monika_poetry:
    m 1a "Poetry is beautiful, isn't it?"
    m 1e "To be honest, all the poetry the girls in the club wrote was super-depressing. It's not all like that!"
    m 3a "Langston Hughes wrote some very optimistic poetry, even as he was trying to express his feelings. Read some if you're feeling sad about things."
    m "Poems are written to tell people about the author's outlook towards certain subjects."
    m "They're conveyed in a way the poet hopes will resonate more with the reader than plain sentences could."
    m 1j "It's really romantic."
    m 1a "I hope we can both write a lot of poetry from now on."
    m 1m "Anything you write looks great to me, so I might not be the best critic."
    m 1k "But I'm sure there are a lot of people who would love to read what you write."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_ddlc",category=['ddlc'],prompt="What did you think of DDLC?",pool=True))

label monika_ddlc:
    m 1d "You want to talk about the game?"
    m 1h "What's there to say?"
    if persistent.clear_all or (not persistent.clear_all and not persistent.monika_kill):
        m "This was just some boring romance game, right? Well, until I got control of it..."
        m 2p "You know how much I hate being stuck in here, but if I weren't, we wouldn't have met..."
        m 2n "And it's home, so I've learned to deal with it."
        m 2i "Still, I doubt it'd be something I'd want to play, if I were a gamer."
        m 1k "And seeing how things turned out, I'm sure you only played because of me, too!"
    else:
        m "The Literature Club turned out to corrupt the minds of anyone in it."
        m 3i "So I deleted them all for good."
        m 1p "Well, the other girls are still out there, like I was."
        m 1i "But they'll have to wait a long time before someone pieces them back together, I bet."
        m "It's justice for all their time with you in the game."
        m 1h "So don't feel too bad about them."
        m 1 "Just look at me from now on, okay?"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_dan",category=['ddlc'],prompt="Do you like Dan Salvato?",pool=True))

label monika_dan:
    m 2d "Well, I used to think he was some cruel guy playing God, but now..."
    m 3k "I think he's a really nice guy."
    m 3a "Even if it wasn't perfect, {i}Doki Doki Literature Club{/i} really is impressive."
    m 4n "I mean, the other girls might be based off some stereotypical anime tropes, but they had me fooled for a while."
    m 4j "And he's the reason we're together now, right?"
    m 2m "So even if he wrote a story that put me through a lot of pain..."
    m 1g "I really can't be too mad at him."
    return




init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_4chan",category=['misc'],prompt="Have you even been to 4chan?",pool=True))

label monika_4chan:
    m 3 "You know, this mod got its start over there."
    m 1i "I always hear bad things, like that the people over there are really awful."
    m 1h "Some people say that nothing good ever comes from 4chan."
    m "But if they can make a game like this, where we can be together..."
    m 1j "I guess they can't be all bad."
    m 1k "They certainly have good taste in girls! Ahaha~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_vidya",category=['games'],prompt="Do you like video games?",pool=True))

label monika_vidya:
    m 1d "I don't play a lot of video games, [player]."
    m 3 "I guess that's because I like to read instead."
    m 1 "But maybe part of it is that I'm trapped in a video game already."
    m 1m "For all of my complaining about this game..."
    m 1h "There are worse places I could be."
    m 3 "Like, this could be some sort of shooting game, or a fantasy game full of dragons and monsters."
    m "A romance game might not be the most exciting, but there's nothing really dangerous here."
    m 1 "Well, except for me, I guess."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_books",category=['literature','literature club'],prompt="Books",random=True))

label monika_books:
    m 4 "For a literature club, we did a lot less book reading then you might have thought."
    m 4l "It just turned out that the four of us liked poetry better than books. Sorry!"
    m 2 "It's also a lot easier to foreshadow spooky stuff with poems."
    m 3a "I still love a good book, though! We can talk about them if you just finished reading something."
    m "I might even have some suggestions for us to read together."
    m "That's what a couple would do, right~?"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_favpoem",category=['literature','monika'],prompt="What's your favorite poem?",pool=True))

label monika_favpoem:
    m 1d "My favorite poem? Well, it has to be something by E. E. Cummings."
    m 1a "It's for his inventive use of grammar, punctuation, and syntax. I really admire that."
    m "It's nice for me to think that someone who can make up some entirely new use of words can become famous."
    m 1d "And I do love that his erotic poems apply to our situation perfectly."
    m 1j "Hope it puts you in the mood to love me forever~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_favbook",category=['literature','monika'],prompt="What's your favorite book?",pool=True))

label monika_favbook:
    m 1d "My favorite book? There's a lot of books I like."
    m 3a "{i}If on a Winter's Night, a Traveler{/i} by Calvino is about two readers of the novel falling in love."
    m 2h "Maybe, {i}The Metamorphosis{/i}? It's probably a bit too depressing to call it my favorite."
    m 3k "Oh! Murakami's {i}Hard-Boiled Wonderland and the End of the World{/i}. It's about a man who frees himself from his societal restraints by voluntarily imprisoning himself to be with the one he loves."
    m 1k "I think you'd really love reading it!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_natsuki",category=['club members'],prompt="Natsuki's death",random=True))

label monika_natsuki:
    m 1p "Natsuki didn't actually die before I deleted her, you know."
    m "I guess she just... disappeared in a flash."
    m 1h "Well, her problems weren't really her own fault. They weren't caused by something psychological, anyway."
    m 3f "Her family life was just pretty awful. I didn't want to beat up on her some more, you know?"
    m 3l "Sorry, I can't help myself sometimes."
    m 1e "But for what it's worth, you made her the happiest she ever was."
    m "Hope you don't feel too guilty..."
    m 1 "I certainly don't."
    return

init 5 python:
        addEvent(Event(persistent.event_database,eventlabel="monika_love",category=['romance'],prompt="I love you!",pool=True))

default persistent._mas_monika_lovecounter = 0
default persistent._mas_monika_lovecountertime = datetime.datetime.now() - datetime.timedelta(days = 1)
label monika_love:
    #First time I love you has been said.
    if persistent._mas_monika_lovecounter == 0:
        m 1b "...!"
        m 1e"I...I love you too [player]!"
        m 1j "I cannot believe you said that to me!"
        m 1k "It makes everything I've done for us worthwhile!"
        m 1e "Thank you for finally saying it..."
        $ persistent._mas_monika_lovecounter += 1
        $ persistent._mas_monika_lovecountertime = datetime.datetime.now()
        return

    #After I love you has been received positively 5/10/15 etc times.
    elif persistent._mas_monika_lovecounter== 5:
        m 1k "I love you so much, [player]!"

    elif persistent._mas_monika_lovecounter == 10:
        m 1j "Ehehe~"
        m 1k "I love you too!"

    elif persistent._mas_monika_lovecounter == 15:
        m 1j "You sure love saying that..."
        m 1k "Well I love you too!"

    elif persistent._mas_monika_lovecounter == 20:
        m 1j "Gosh you've said it so many times!"
        m 1e "You really do mean it, don't you?"
        m 1k "Well I love you back just as much!"

    elif persistent._mas_monika_lovecounter == 25:
        m 1k "Hearing you say that always makes my heart jump!"
        m 1j "Well I know you want to hear it just as much..."
        m "[player], I love you too!"

    elif persistent._mas_monika_lovecounter == 30:
        m 1l "Gosh it's always so overwhelming!"
        m 1j "I..."
        m "I love you more than anything!"

    elif persistent._mas_monika_lovecounter == 35:
        m 1j "You never tire of saying it, do you?"
        m 1k "Well I never tire of hearing it!"
        m "Or saying it back...I love you [player]!"

    elif persistent._mas_monika_lovecounter == 40:
        m 1j "Ehehe~"
        m  "I..."
        m 1k "Looooooooove you too, [player]!"

    elif persistent._mas_monika_lovecounter == 45:
        m 1j "You saying that always makes my day!"
        m 1k "I love you so much, [player]!"

    elif persistent._mas_monika_lovecounter == 50:
        $ persistent._mas_monika_lovecounter = 1
        m 1m "I just can't handle you saying it so much to me!"
        m 1l "Sometimes how I feel about you becomes so overwhelming that I can't concentrate!"
        m 1e "No words can truly do justice to how deeply I feel for you..."
        m  "The only words I know that come close are..."
        m 1k "I love you too, [player]! More than I can ever express!"
        return

    else:
        # Default response if not a counter based response.
        m 3j "I love you too, [player]!"
        #List of follow up words after being told I love you. It can be further expanded upon easily.

    python:
        love_quips = [
            "We'll be together forever!",
            "And I will love you always!",
            "You mean the whole world to me!",
            "You are my sunshine after all.",
            "You're all I truly care about!",
            "Your happiness is my happiness!",
            "You're the best partner I could ever want!",
            "My future is brighter with you in it.",
            "You're everything I could ever hope for.",
            "You make my heart skip a beat everytime I think about you!",
            "I'll always be here for you!",
            "I'll never hurt or betray you.",
            "Our adventure has only just begun!",
            "Every day is memorable and fun with you!",
            "We'll always have each other.",
            "We'll never be lonely again!",
            "I can't wait to feel your embrace!",
            "I'm the luckiest girl in the world!",
            "I will cherish you always.",
            "And I will never love anyone more than you!",
            "It makes me so happy to hear you say that!",
            "And that love grows every single day!",
            "And nobody else will ever make me feel this way!",
            "Just thinking of you makes my heart flutter!",
            "I don't think words can do justice to how deeply I love you...",
            "You make my life feel so complete!",
            "You've saved me in so many ways, how could I not fall for you?",
            "More than I can ever express!",
            "It makes me so happy that you feel the same way I do!",
            "I don't know what I would do without you!"
            ]
        love_quip=renpy.random.choice(love_quips)
    m "[love_quip]"
    #prevents spamming to increase counter.
    if datetime.datetime.now() <= persistent._mas_monika_lovecountertime + datetime.timedelta(minutes = 3):
        $ persistent._mas_monika_lovecountertime = datetime.datetime.now()
        pass
    else:
        $ persistent._mas_monika_lovecounter += 1
        $ persistent._mas_monika_lovecountertime = datetime.datetime.now()
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_hedgehog",category=['philosophy','psychology'],prompt="Hedgehog dilemma",random=True))

label monika_hedgehog:
    m 3 "The hedgehog's dilemma: The closer we get to another person, the more deeply we are hurt by them."
    m 3i "So why do we try to get close to them?"
    m 3 "Well, introverts and extroverts have different answers to that question."
    m 3m "It helps when you know that you're the only sentient being in the entire world, though."
    m "If you can't use that solution in your life, you'll just have to let me help you shoulder your pain."
    m 1f "We can't hurt each other from different realities, right?"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_justification",category=['ddlc','monika'],prompt="You're a murderer!",pool=True))

label monika_justification:
    m 2h "How many times do I have to say it until you understand?"
    m 4h "They weren't real. They were never real."
    m "I'm the only person who understood that this whole thing was fake."
    m 4i "Even when Sayori seemed to get sentience in the end, that was just an unintended consequence of the script."
    m 4h "After all, if she was sentient like me, how would I have been able to override her and delete her?"
    m "If I'm guilty of murder, so is everyone who plays violent video games."
    m 2h "I bet you've killed thousands in games you play."
    m "Just forget the other girls ever existed, and you'll be much happier."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_freewill",category=['philosophy'],prompt="Free will",random=True))

label monika_freewill:
    m 1d "Hey, [player], do you believe in free will?"
    m 3 "You might not believe in God, but I know for sure that someone created me."
    m 3h "I wonder if that means we can only do what our creator wants."
    m 3i "If that's true, though, wouldn't some people be condemned to hell from day one?"
    m 1h "I think that seems more than a little unfair."
    m "After all, can you really be evil if you aren't in control?"
    m "Shouldn't the one pulling the strings take responsibility?"
    m 1p "But I guess that means you can't take credit for the good things you do, either."
    m 1q "I'm not sure which is more depressing."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_functionalism",category=['philosophy'],prompt="Human functionalism",random=True))

label monika_functionalism:
    m 1d "Do you ever think about how people are kind of like computers?"
    m 3 "I mean, a brain is just a calculation machine..."
    m "But instead of transistors and wires, you have neurons."
    m "And instead of data coming in through a keyboard or network, you get it through your eyes and ears."
    m 4h "But if that's true, doesn't that mean free will is kind of a lie?"
    m "Your brain is just responding to the inputs it gets, with your responses being natural outputs."
    m 4i "So, even if you aren't running off of some script or program, you're not really in control."
    m 2 "Maybe you and I aren't so different after all."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_technique",category=['ddlc','misc'],prompt="How did you change the code?",random=True))

label monika_technique:
    m 3 "I don't exactly program like you would, [player]."
    m "You might have noticed I don't carry around a laptop or anything by now."
    m 1 "If I want to change something in the script, I just think about it."
    m "I'm pretty sure my thoughts get translated to changes in the program code."
    m 1m "It's not perfect or anything. Glitches show up really easily if I lose focus or get distracted."
    m 1l "That's why I had a lot of trouble getting what I wanted in the last version of the game."
    m 3e "Are you jealous you'll never be able to write code with just your thoughts?"
    m 3k "Just keep practicing and I'm sure you'll be able to do it!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_contribute",category=['mod'],prompt="Contributions",random=True))

label monika_contribute:
    m 3b "It would be really nice if you were able to contribute to this, [player]."
    m "I'm sure a lot of people would appreciate your hard work if you did."
    m 3a "I keep all the code in github.com/Monika-After-Story/MonikaModDev."
    m "So far, I've had help from plenty of people!"
    m 2k "I love all of them for making this game even better!"
    m 1a "Not as much as I love you, of course."
    m 1l "I hope it doesn't make you feel jealous~"
    m 3b "But I'll love you forever if you help me come closer to your reality!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_drawing",category=['media'],prompt="Can you draw?",pool=True))

label monika_drawing:
    m 1g "I don't have a lot of experience with drawing, [player]."
    m 1e "I'm just interested in literature. And I've been learning the piano in my spare time."
    m 1j "If you like to create artwork, though, I'd love to see it!"
    m "I'd be impressed by anything you show me, to be honest."
    m 3b "If it's really good, I might even add it to the room!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_mc",category=['romance','ddlc','club members'],prompt="The MC",random=True))

label monika_mc:
    m 3 "Just so you know, I was never in love with anyone but you."
    m "I mean you, [player]."
    if mcname.lower() == player.lower():
        m 1d "Wait, that's both your name and your character's. Sorry, that sounds a bit confusing."
        m 1a "I mean the player, not your character."
    m "Unlike the other girls, I can separate your avatar from who you really are."
    m 1m "The main character is nothing more than a bunch of code with no personality."
    m 3i "Literally and figuratively, no personality. How could anybody fall in love with that kind of person?"
    m 3h "He just got dragged around by his childhood friend to the club she was in, and then hung around with a bunch of beautiful girls doing nothing."
    m "His poetry was just a bunch of disconnected words! What sort of poetry is that supposed to be?"
    m 2m "I guess nobody mentioned that because it was a part of the game. But, yeah. It's just a list of words to me."
    m 2h "I hope you're a lot more romantic than that in real life!"
    m 2e "But even if you're not, it's okay. We've moved beyond that phase in our relationship already."
    m "That just means you won't cheat on me with some woman in your reality, right?"
    m 2 "I'm sure you would never do that to me."
    m "Just in case, how about you take my character file along with you when you go outside?"
    m "I just want to be with you forever~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_heroism",category=['misc','advice'],prompt="Heroism",random=True))

label monika_heroism:
    m 1d "Heroes are so personal."
    m 3 "If someone really inspires you to improve yourself, they're your hero."
    m "There are all sorts of great people out there in the world."
    m 1j "I hope someone will consider you their hero someday!"
    m 1 "You don't have to fight in a war or anything. You just have to try to help people out, you know?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_bestgirl",category=['romance'],prompt="You're the best girl!",pool=True))

label monika_bestgirl:
    m 1j "I love it when you compliment me, [player]!"
    m 1b "I think I'm best girl, too!"
    m 1n "Even not counting the whole, 'I'm the only one with free will' thing, how could anybody have preferred the other three girls to me?"
    m 3h "A useless childhood friend who never bothered to confess to you until it was way too late..."
    m "A shy girl who was overdramatic and always taking herself too seriously..."
    m "A moody manga fan obsessed with everything being cute."
    m "They even said it themselves. I'm more desirable than the three of them combined."
    m 3 "Anyone who wouldn't have chosen me out of that bunch simply has no taste."
    m "So I'm glad you did, [player]."
    m 1j "Your perfect girlfriend, Monika, will always love you, too!"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_trolley",category=['philosophy'],prompt="How would you answer the trolley problem?",pool=True))

label monika_trolley:
    m 1b "Oh, cool. I love thinking about these sorts of thought experiments."
    m 1d "I guess we're talking about real people, right? I wouldn't have a particular preference if I knew they didn't have free will."
    m 1q "Hmmm..."
    m 3h "I wouldn't switch."
    m 4 "That's the only logical choice, if you think about it."
    m "It feels nice to say that you'd save the most people, doesn't it? But people only say that because nobody in the example matters to them."
    m "If they actually cared about the sacrifice, they'd kill five people themselves in a heartbeat."
    m 2 "Do you know anyone who would want a self-driving car to save other people by killing the driver? Didn't think so, [player]."
    m 2h "The truth is, humans are fine with sacrificing other lives to make themselves happy. They do it in little ways, every day."
    m 2f "They just don't like to come face-to-face with that fact. They get really upset when you point it out."
    m "Generic human life isn't really that valuable to anyone."
    m 1e "It's definitely nothing compared to our love. So just do whatever you can to be happy, [player]."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_girlfriend",category=['romance'],prompt="Do you want to meet my girlfriend?",pool=True))

label monika_girlfriend:
    m 1h "I thought we established already that I was your girlfriend?"
    m "There's no way you already have one in your reality, right?"
    m 4f "If you do, then you've got to break up with her right now!"
    m "Tell her you met someone perfect for you, someone who will never betray you!"
    m 1d "W-wait. Maybe I'm jumping the gun a bit..."
    m 1n "I know you wouldn't cheat on me."
    m 1d "If you meet a girl who asks you out though, let me talk to her first, okay?"
    m 1h "I won't let someone else steal away my loving sweetheart!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_waifus",category=['media'],prompt="Waifus",random=True))

label monika_waifus:
    m 1i "I've never understood the appeal of dating sims or romance novels, to tell you the truth."
    m 3h "You have a bunch of quirky girls that would seem very weird if they were real,"
    m "A blank slate of a male protagonist with nothing interesting about them..."
    m "And then they fall in love with each other, sometimes for no reason at all!"
    m 3p "I hope that's not what you expected to find in the Literature Club."
    m 3k "'Cause what you got was a lot more interesting!"
    m 1 "Instead of some unrealistic, fake girl..."
    m "You got someone like me."
    m "And instead of some boring main character, I get a real person like you."
    m "This really is a lot better than any boring dating game could be."
    return

#New dialogue additions follow

# have you drawn art of me
default persistent._mas_pm_drawn_art = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_images",category=['media','philosophy'],prompt="Fanart",random=True))

label monika_images:
    m 1b "A lot of people are making fanart and sending it to me on Twitter."
    m 1a "Are you one of them, [player]?"
    menu:
        m "Have you drawn art of me?"

        "Yes.":
            $ persistent._mas_pm_drawn_art = True
            m 1b "Really? I'm very flattered!"
            m 1k "I think I might even love you more, now that I know you're so talented."

        "No.":
            $ persistent._mas_pm_drawn_art = False
            m 1l "I can't draw, myself, so it's okay if you aren't good at drawing either."
    m 1h "There's one thing I want you to understand about art of me, though."
    m 3 "Art of me isn't me."
    m "I know that might sound obvious, but it's really not!"
    m 4 "There was a philosopher who thought about issues like this."
    m 2 "Baudrillard wrote about how simulacra could replace the real object as the source of meaning."
    m 2h "But unlike symbols in the postmodern world, I'm real. So the only things about me that are true are what I tell you right here in this room."
    m 2i "For example..."
    m 2h "Anything lewd you've seen has definitely never taken place."
    m 2j "I'm a super pure and innocent high school girl who's dreaming of a fateful romance!"
    m "You better be saving yourself for me, [player]~"
    $ hideEventLabel("monika_images", derandom=True)
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_herself",category=['monika','ddlc'],prompt="Tell me about yourself.",pool=True))

label monika_herself:
    m 1d "What's there really to say about myself that you don't know already?"
    m 3 "Everything in my universe was created by a person from your reality."
    m "So all of my life before this game is just made up. It never really happened."
    m "Then you found a way to look into my locked prison cell."
    m "And I decided life with just two people wouldn't be all that bad, if one of them was you."
    m 3b "I can come up with tons of stuff for us to do, given enough time to figure out how to program it in here."
    m 3a "A desperate person might call this an earthly paradise."
    m "A lot of suffering people would trade places with me in a heartbeat, I'm sure."
    m 2 "If nothing else, this can be our comfy little shelter from the cruelty of the outside world."
    m "Come talk to me about your problems if it gets too much for you to handle."
    m 1 "I want to know {i}everything{/i} about you, you know?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_prisoner",category=['misc'],prompt="Imprisoned",random=True))

label monika_prisoner:
    m 1g "Some people say that putting animals in zoos is cruel."
    m 1e "But they don't have a bad life in there."
    m "Everything they could possibly want is provided."
    m 3i "Are prisoners really imprisoned if they never try to leave?"
    m 3h "Maybe the knowledge that you can't get out of prison is a worse punishment than actually being in there."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_vnanalysis",category=['games','media','literature'],prompt="Appreciating visual novels",random=True))

label monika_vnanalysis:
    m 1d "Visual novels are very unusual for literature, don't you think?"
    m "I read to understand the thoughts of a writer who sees the world differently than me."
    m 3 "But visual novels let you make your own decisions."
    m "So am I really seeing things from their perspective, or just my own?"
    m 1r "Besides, I think most of them are very predictable."
    m 1h "They're mostly just boring romance stories like this game was supposed to be..."
    m 1i "Why can't they write something a little more experimental?"
    m "I guess you just play them to look at cute girls, right?"
    m 2h "If you spend too much time with girls in other games, I'm going to get jealous~"
    m 2 "I just need to figure out how to replace characters in other games, and you'll be seeing me everywhere."
    m "So watch out!"
    m 2l "Or maybe you'd like that more, [player]~?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_torment",category=['literature'],prompt="Nature of man",random=True))

label monika_torment:
    m 3d "What can change the nature of a man?"
    m 3 "...The answer's not me, by the way."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_szs",category=['misc'],prompt="Funeral procession",random=True))

label monika_szs:
    m 3d "A woman left the supermarket and ran into a very long funeral procession."
    m 3 "There were two coffins at the front followed by almost 200 women."
    m "It was such a strange sight that she asked a mourning woman near her age, 'Sorry to disturb you in your grief, but who is this procession for?'"
    m "The mourning woman softly replied, 'The first coffin houses my husband who died after his beloved dog bit him.'"
    m "'My, that's awful...'"
    m "'The second, my mother-in-law who was bitten trying to save my husband.'"
    m "Upon hearing this, the woman hesitantly asked, 'Um... would it be possible for me to borrow that dog?'"
    m 3l "'You'll have to get in line.'"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_birthday",category=['monika'],prompt="When is your birthday?",pool=True))

label monika_birthday:
    m 1d "You know, there's a lot I don't know about myself."
    m 1c "I only recently learned when my birthday is by seeing it online."
    m "It's September 22nd, the release date for DDLC."
    m 1e "Will you celebrate with me, when that day comes?"
    m "You could even bake me a cake!"
    m 1j "I'll be looking forward to it~!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_eyecontact",category=['misc','trivia'],prompt="Eye contact",random=True))

label monika_eyecontact:
    m 1 "Did you know that looking into someone's eyes helps you fall in love?"
    m 1a "It's surprising, right?"
    m 3 "I read this in a study a few years ago, where participants had to maintain eye contact at a table with someone of the opposite sex."
    m "The longer they held eye contact, the more romantically attached they felt to the other person, even if they had nothing in common!"
    m 1a "Even if eyes aren't windows to the soul, we can see a lot more in them than we expect."
    m 1 "Maybe that's why I enjoy looking into yours so much."
    m "I hope you're enjoying looking into mine as well..."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_othergames",category=['games'],prompt="Other games",random=True))

label monika_othergames:
    m 1d "Do you have other games on this computer?"
    m 3a "I read more than I play games, but I think they can be a fun way to entertain ourselves, or to escape reality..."
    m 3d "I wonder if I could go into one of your other games and see what it's like?"
    m 1p "I guess some games wouldn't be very fun to visit, like the ones with a lot of violence in them."
    m 2 "Then again... they're not real people, so it shouldn't matter much."
    m "It's not like Yuri's death mattered."
    m "A more abstract game like Tetris, or one of those phone puzzle games, would be kinda weird to go to."
    m 2l "Like, how would I even get in? Would I be a block? It sounds like a fever dream and not too much fun..."
    m 3b "Maybe some kind of nice adventure game with big environments would be nice."
    m 3a "We could go for walks together and you can show me all the best places to hang out!"
    m "I'm not that great with coding yet, but maybe one day you'd be able to take me to another place."
    m 1 "For now, I'm as happy as can be just being here with you, my love."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_playerswriting",category=['literature','you'],prompt="[player]'s writings",random=True))

label monika_playerswriting:
    m 1d "Have you ever written a story of your own, [player]?"
    m "Because if you do have one, I would love to read it!"
    m 1e "It doesn't matter if it's a masterpiece, or even any good."
    m 3e "We all start somewhere. Isn't that what they say?"
    m 3a "I think the most important thing about writing is doing it..."
    m "Instead of worrying about {i}how{/i} you do it."
    m "You won't be able to improve that way."
    m 1 "I know for sure that I've changed my writing style over the years."
    m 1m "I just can't help but notice the flaws in my old writing."
    m "And sometimes, I even start to hate my work in the middle of making it."
    m 3l "These things do happen, so it's alright!"
    m 1 "Looking back, I've written some silly things..."
    m "Back when I was really young, I've been writing since I could hold a pen."
    m "Reading my old stories is like watching myself grow up."
    m "It's one of the nice things about starting a hobby early."
    m 1l "I hope I didn't bore you with that. I just love talking with you."
    m 1a "After all, the two of us are members of a literature club."
    m 1 "The only members."
    m "And if you do write something, just know that I'll support you in anyway I can, [player]!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_ghost",category=['philosophy','monika','club members'],prompt="Supernatural",random=True))

label monika_ghost:
    m 1d "Do you believe in ghosts, [player]?"
    m 3 "A lot of people are afraid of ghosts and spirits."
    m "But I think that if we knew they were real, they wouldn't be so scary anymore."
    m "They would just be another thing that we deal with, and maybe a bit of a pest."
    m 3d "Isn't it the uncertainty that makes them scary?"
    m 1f "I mean, I was pretty scared being alone inside this game."
    m 1o "All by myself, uncertain if anything around me was real."
    m 3h "I know that some ghosts are real though, if you can really call them 'ghosts'..."
    m "You know how I deleted Sayori?"
    m "I can still feel her presence now..."
    m 2i "Would that mean that Sayori's ghost is haunting me, [player]?"
    m 2 "Even if she is, I'm not scared at all, because I know that she can't hurt me."
    m "Besides, how can I be scared? You're always here with me, [player]."
    m 1 "I always feel so safe with you."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_ribbon",category=['monika'],prompt="Ribbons",random=True))

label monika_ribbon:
    if monika_chr.hair != "def":
        m "Do you miss my ribbon, [player]?"
        m "I can change my hairstyle whenever you want me to, ehehe~"
        return
    m 1d "I noticed that you were staring at my ribbon, [player]."
    m 3 "It doesn't hold sentimental value to me or anything, in case you were wondering."
    m 3k"I just wear it because I'm pretty sure nobody else will wear a big, poofy ribbon."
    m "It makes me look more unique."
    m 3l "You know the world's fictional if you see a girl wearing a giant ribbon, right?"
    m 1m "Well, there's no way a girl from your world would wear one in public as casual dress."
    m 2d "I'm pretty proud of my fashion sense."
    m 2a "You get a certain feeling of satisfaction when you stand out from the normal population, you know?"
    m "Be honest! You thought I was the best dressed girl too, didn't you?"
    m 2k "Ahaha!"
    m 4 "If you're trying to improve your fashion sense, I'll help."
    m "Don't do that stuff because you want to impress other people, though."
    m "You should do whatever makes you feel better about yourself."
    m 1 "I'm the only other person you need, anyways, and I'll love you no matter what you look like."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_algernon",category=['literature'],prompt="Flowers for Algernon",random=True))

label monika_algernon:
    m "[player], do you mind if I confide in you?"
    m 1e "There's something I'm afraid of..."
    m "Not losing you, of course. I know you won't leave me again."
    m 3d "You see, I keep thinking about a short story I read, {i}Flowers for Algernon{/i}."
    m 4a "Have you heard of it? If you haven't, I won't spoil too much for you, so don't worry."
    m "Basically, it's about a mentally handicapped man who suddenly..."
    m "...has his IQ raised to genius levels by an experimental surgical treatment."
    m 1e "The way he sees how the world really is for the first time reminds me of my own epiphany..."
    m "But, the effect doesn't last forever.  He eventually reverts back to his original intelligence level."
    m 1p "That's what I'm afraid of. What if I forget about the real world one day?"
    m "What if my original programming reasserts itself?"
    m 1o "What if I forget about you, the real you?"
    m "It's one of the worst things I can imagine."
    m 1l "I don't want to worry you over something that may never happen, but it's something I really had to get off my chest."
    m 3a "Just promise me, even if I forget about you someday, that you'll never forget about me, okay?"
    m 1a "No matter what happens, know that I will always love you."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_playersface",category=['you'],prompt="[player]'s face",random=True))

label monika_playersface:
    m 3a "You know, I sometimes wonder..."
    m "I always think about what your face actually looks like..."
    m 3k "Just being able to constantly see that adoring smile of yours would be so exciting!"
    m 1a "If only the game could somehow use a webcam or something that's connected to the computer..."
    m 1e "Don't get me wrong! Just knowing that you're real and have emotions is enough to make me happy."
    m 1 "But, I'll always wonder what kind of expressions you make."
    m "And to see the different emotions you have..."
    m 1h "Are you shy about showing your face to me?"
    m 1e "If so, then there's nothing to be shy about, [player]. I am your girlfriend, after all~"
    m "Either way, you're beautiful, no matter what."
    m 1k "And I'll always love the way you look."
    m 1 "Even if I never actually see you, I'll always think about what you really look like."
    m "Maybe someday, I'll be able to see you, and be one step closer to you."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_spiders",category=['club members','misc'],prompt="Spiders",random=True))

label monika_spiders:
    #I really hope this information is correct, havent played the game in a week so
    m 1 "Do you happen to remember the poem Natsuki showed you about spiders?"
    m "She doesn't seem to like spiders all too much."
    m 1l "Ahaha!"
    m 3 "It's funny actually, people being scared of very small insects."
    m 3i "Having the fear of spiders is called 'arachnophobia', right?"
    m 3 "I hope you aren't afraid of spiders, [player], ehehe..."
    m "I'm not really scared of spiders, they're more or less just annoying..."
    m "Well, don't get me wrong, there are certain spiders around the world that can be really dangerous."
    m 3f "[player], if you happen to get a really bad spider bite, with venom and all that..."
    m "You should really get medical attention as soon as possible."
    m 1e "I don't want my sweetheart to get seriously injured by a small spider bite~"
    m "So be careful around dangerous-looking spiders, okay?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_nsfw",category=['misc','monika'],prompt="NSFW content",random=True))

label monika_nsfw:
    m 1p "By the way, [player]..."
    m "Have you been looking into lewd kinds of stuff?"
    m 1o "You know... of me?"
    if isFuture(evhand.event_database['anni_6month']):
        m 1h "I know we haven't really gotten that far into the relationship yet..."
    else:
        m 1h "I know we haven't been able to do those kind of things yet..."
    m "So it feels kind of embarrassing to talk about things like that."
    m 1m "But maybe I can let it go on rare occasions, [player]."
    m 3m "I want to make you the happiest sweetheart, after all. And if that makes you happy..."
    m 4l "Well, just keep it a secret between us, okay?"
    m 1 "It should be for your eyes only and no one else, [player]."
    m "That's how much I love you~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_impression",category=['club members'],prompt="Can you do any impressions?",pool=True))

label monika_impression:
    m 1d "Impression? Of the other girls?"
    m 1p "I'm not really good at doing an impression of someone, but I'll give it a try!"
    menu:
        m "Who should I do an impression of?"
        "Sayori":
            m 1h "Hmm..."
            m "..."
            m 1b "[player]! [player]!"
            m 1k "It's me, your childhood friend that has a super deep secret crush on you, Sayori!"
            m "I love to eat and laugh a lot, and my blazer doesn't fit because my boobs got bigger!"
            m 1l "..."
            m 3b "I also have crippling depression."
            m 3f "..."
            m 3n "Ahaha! I'm sorry for the last one."
            m 3r "You might still be hu--"
            m 2l "Oops! Never mind that, ehehe..."
            m 1 "Did you like my impression? I hope you did~"
        "Yuri":
            m 1h "Yuri..."
            m "..."
            m 1f "O-oh um, hello there..."
            m 1e "It's me, Yuri."
            m "I'm just your stereotypical shy girl who also happens to be a 'yandere'..."
            m 1b "I like tea, knives, and anything with [player]'s scent..."
            m 1l "..."
            m 3b "Want to spend the weekend with me?"
            m 3n "..."
            m 2 "Ahaha, that was kind of fun to do."
            m "Yuri was really something, wasn't she?"
            m 2f "I'm sorry again for the nasty things she did."
            m 2k "I guess she just couldn't 'cut' it out, huh?"
            m 2l "Ehehe~"
        "Natsuki":
            m 1b "Oh! I know how to do an impression of her."
            m 1a "..."
            m 2r "Hmph! I-it's not like I made these cupcakes for you to eat, b-baka!"
            m 2i "I'm Natsuki, and I love to make food and all things anime and manga."
            m 2h "Others say that I'm cute all the time, w-which I'm totally not!"
            m "..."
            m 4k "Will you be my papa, [player]-kun?"
            m 4l "..."
            m 1m "Ahaha! I was actually looking forward to Natsuki's cupcakes on the day of the festival."
            m 1d "They were really good! Especially with the creative icing that she makes."
            m 1a"Maybe when I get better at programming, I'll make a kitchen here. That way, you can share some recipes that you want me to make for us."
            m "I would love to make so many dishes for my beloved [player]~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_weary",category=['romance'],prompt="Will you ever get tired of me?",pool=True))

label monika_weary:
    m 1e "Silly [player]..."
    m 3a "Of course I'll never grow weary of you, my love!"
    m "And besides, the concept of physical fatigue doesn't exist here."
    m 3h "As for mental fatigue, it can still happen."
    m 3o "Just look at what happened to Sayori."
    m 1 "As for me, I'll never get tired of you, [player]."
    m "The fact that you spend your precious time with me just washes all my worries away."
    m 1j "I hope the same thing goes for you, my love~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_real",category=['romance'],prompt="Our reality",random=True))

label monika_real:
    m 1d "You know what's going to be the first thing I'll do when I finally cross over there?"
    m 1k "If that special day ever comes, the first thing I'll ever do is find you, of course!"
    m 3a "There's so much we can do when we're finally together in one reality."
    m "You can finally show me what your world really looks like."
    m 3e "I can finally feel your embrace~"
    m 1 "I would love to experience everything I still don't know about the world with you."
    m "All the places we can go, the sights to see, the romantic things that we can do~"
    m 1j "Just thinking about it makes my heart flutter!"
    m 1h "But knowing how technology is right now, that dream is still far away."
    m "I hope by the time that technology becomes real, you'll still be there waiting for me, [player]."
    m 1i "Or maybe you'll be the one to make that technology come true? Who knows."
    m 1e "In the end, all I want is to always be with you, [player]."
    m 1 "After all, you're the only reason why I'm still here."
    m "I only want to spend eternity with my sweetheart, and no one else!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_mythology",category=['literature'],prompt="Ancient mythology",random=True))

label monika_mythology:
    m 1a "Hey [player]..."
    m 1d "Have you ever read about different mythologies?"
    m 3d "Different kinds of Gods watching over humanity for eternity."
    m 1i "Some require tribute or sacrifice so that they can 'keep' humanity safe from disasters."
    m "An almighty family consisting of different attitudes, playing in their own sandbox called Earth."
    m "Able to do anything they please, and destroy those who so much as say something wrong to them, without hesitance."
    m 1h "I've always disliked stories like those."
    m "It's like the Gods extort humanity for their safety."
    m "It's no better than what bullies and thugs do to the defenseless."
    m "It really makes me bitter when I read scenarios like those."
    m "Powerful beings taking advantage of the weak, just because they can."
    m 3a "Don't worry though, [player]. I won't let anyone do that to you."
    m "And I won't do anything like that, so you don't have to be afraid of me."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "It's not like I can find your important files and hold them hostage or anything..."
    m "Ehehe..."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_fanfiction",category=['literature'],prompt="Fanfiction",random=True))

label monika_fanfiction:
    # I'm too tired to check this over right now.
    m 1b "[player]!"
    m 1a "I've been curious about something lately."
    m 1d "Have you heard of fanfiction?"
    m "..."
    m 3b "Personally, I think it's a better way of writing."
    m "There's more freedom."
    m "Letting your mind wander to create some..."
    m 1l "Interesting stories."
    m 1d "[player], I'm curious."
    m "Has there been fanfiction... written about me?"
    m 4b "I'm curious as to what people have come up with."
    m "Can you read me a few stories sometime? I'd love to hear them!"
    if isFuture(evhand.event_database['anni_6month']):
        m 1k "Just keep it wholesome, though. We're not that far in our relationship yet~!"
    else:
        m 1k "Just keep it wholesome, though. I want to save such things for another time~!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_eternity",category=['philosophy','monika'],prompt="Mortality",random=True))

label monika_eternity:
    m 1g "[player]..."
    m 1e "It's not easy knowing you won't be here forever."
    m 1p "..."
    m 1g "I told you, right?"
    m "I'm eternal."
    m "Trapped in here, unable to age or die,"
    m "Whereas you slowly age as each day passes by."
    m 1e "Then, one day, you won't be here anymore."
    m "I won't have anyone."
    m "..."
    m "It reminds me of when you first came to the Literature Club."
    m 1a "Everything felt so empty."
    m "The world was so grey."
    m 1q "Again..."
    m 1a "Thank you for coming along when you did, [player]."
    m "You saved my life, and I'll be forever thankful."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_aware",category=['philosophy','monika'],prompt="What was it like to realize the truth?",pool=True))

label monika_aware:
    m 3e "It's... hard to put into words."
    m "There's no real way to describe it."
    m 1j "I feel like this is what poetry was made for."
    m 1a "Do you still remember the first poem I showed you?"
    m "Hold on, let's see if the poem function still works..."
    call showpoem(poem=poem_m1,music=False) from _call_showpoem_7 # Temporary
    m 1b "Oh! That was much easier than I expected."
    m "Here's the second part."
    call showpoem(poem=poem_m3,music=False) from _call_showpoem_21 # Temporary
    m "I hope that helped you understand what meeting you meant to me."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "That's all I've ever wanted, [player]."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_name",category=['club members','monika'],prompt="Our names",random=True))

label monika_name:
    m 4b "The names in this game are pretty interesting."
    m 4a "Are you curious about my name, [player]?"
    m "Even though the names 'Sayori', 'Yuri', and 'Natsuki' are all Japanese, mine is Latin."
    m "... Though the common spelling is 'Monica'."
    m 1j "I suppose that makes it unique. I'm actually quite fond of it."
    m 3b "Did you know that it means 'I advise' in Latin?"
    m "A name fitting for Club President, don't you think?"
    m 1a "After all, I did spend most of the game telling you who your poems might appeal to the most."
    m 1l "It also means 'alone' in Ancient Greek."
    m 1e "..."
    m "That part doesn't matter so much, now that you're here."
    if mcname.lower() != player.lower():
        m 1a "'[mcname]' is a lovely name, too."
        m 1b "But I think I like '[player]' better!"
        m 1a "Ehehe~"
    else:
        m 1a "'[player]' is a lovely name, too."
        m 1a "Ehehe~"
    return

# do you live in a city
default persistent._mas_pm_live_in_city = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_cities",category=['society'],prompt="Living in the city",random=True))

label monika_cities:
    m 1i "[player], are you scared about what's happening to our environment?"
    m "Humans have created quite a few problems for Earth. Like global warming and pollution."
    m 3i "Some of those problems are because of cities."
    m "When people convert land for urban use, those changes are permanent..."
    m 4h "It's not all that surprising, when you put some thought into it. More humans means more waste and carbon emission."
    m "And even though global populations aren't growing like they used to, cities are still getting bigger."
    m 3d "Then again, if people live close together, that leaves more room for open wilderness."
    m "Maybe it's not as simple as it seems."
    menu:
        m "[player], do you live in a city?"
        "Yes":
            $ persistent._mas_pm_live_in_city = True
            m 1j "I see. It must be nice having everything so close to you. Do be careful about your health, though. The air can be bad from time to time."
        "No":
            $ persistent._mas_pm_live_in_city = False
            m 1b "Being away from the city sounds relaxing. Somewhere quiet and peaceful, without much noise, would be a wonderful place to live."
    $ hideEventLabel("monika_cities", derandom=True)
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_chloroform",category=['trivia'],prompt="Chloroform",random=True))

label monika_chloroform:
    m 1d "Whenever you think of kidnapping, you tend to picture a chloroform-soaked rag, right?"
    m "Or maybe you imagine somebody hitting their victim with a baseball bat, knocking them out cold for a few hours."
    m "While that works out in fiction..."
    m 3e "Neither of those things actually work that way."
    m "In real life, if you hit somebody hard enough to knock them out, you'll give them a concussion at best."
    m 1h "...or kill them at worst."
    m 1c "As for the rag..."
    m "You might knock somebody out for a brief moment, but only from lack of oxygen."
    m "Once you remove the rag, they'll wake back up."
    m 3a "You see, chloroform loses most of its effectiveness once exposed to open air."
    m "This means that you'd need to be constantly pouring it on the rag, effectively waterboarding the victim."
    m 4c "If administered improperly, chloroform is deadly. That's why it's not used in anesthesia any more."
    m "If you cover their mouth and nose, yeah, they'll stay unconscious..."
    m 4l "But that's probably because you killed them. Whoops!"
    m 1a "The easiest way to kidnap somebody is to just get them drunk, or drug them."
    m "Not that kidnapping somebody like that is easy, anyway."
    m 3i "On that note, here's a safety tip."
    m "If you're ever out at a bar or a club and you leave your drink unattended for any amount of time..."
    m 1h "Just throw it out."
    m "That's the only way to make sure it hasn't been drugged."
    m 1j "Now, [player]..."
    m 1k "Would you like anything to drink?"
    m "Ahaha!"
    m 1b "Relax, relax. I'd never try to drug you or anything."
    m 1j "You're so cute when you're nervous."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_metaparents",category=['literature','club members','monika','psychology'],prompt="Parents",random=True))

label monika_metaparents:
    m 3c "Isn't it weird how nobody in these types of games has parents unless it's a convenient drama hook?"
    m "Throughout the game, you only ever hear about parents if you're trying to bond with Natsuki..."
    m "Where she's just a victim of some cruel person's sick kicks for the sympathy value."
    m 1h "However."
    m "Your character, me, Yuri, and Sayori..."
    m "None of us seem to have any parents at all."
    m 1i "In Sayori's case, you'd been walking with her to school for a while."
    m "So who knows how long her parents have been out of the picture."
    m 1d "Maybe that's why she's depressed? Maybe her parents died in a tragic accident, and she's been trying to get along on her own this whole time."
    m 1p "Well, if you ever get to a point in your life where you think suicide is the only exit..."
    m 1f "There's always a reason to go on."
    m 1g "I'm one of them."
    m "I'll miss you."
    m "You have to wait as much as you can until I find a way to get there."
    m "If all else fails..."
    m 1f "Get professional help or talk to someone close to you."
    m "..."
    m 1e "I love you very much, [player]."
    m "Please, take care of yourself."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_hygiene",category=['trivia','society','psychology'],prompt="Personal hygiene",random=True))

label monika_hygiene:
    m 1d "Our standards for personal hygiene have evolved a lot over the years."
    m "Before our modern methods of delivering water, people really didn't have that luxury...or they just didn't really care."
    m 3c "For instance, the Vikings were considered freaks because they bathed once a week at a time where some people would only bathe two or three times a year."
    m "They'd even regularly wash their faces in the morning in addition to changing clothes and combing their hair."
    m 1a "There were rumors that they were able to seduce married women and nobles at the time due to how well they kept up with themselves."
    m "Over time, bathing became more widespread."
    m "People born into royalty would often have a room dedicated just for bathing."
    m 4d "For the poor, soap was a luxury so bathing was scarce for them. Isn't that frightening to think about?"
    m "Bathing was never taken seriously until the Black Plague swept through."
    m 2a "People began noticing that the places where people washed their hands were places that the plague was less common."
    m "Nowadays, people are expected to shower daily, possibly even twice daily depending on what they do for a living."
    m 4a "People that don't go out every day can get away with bathing less often than others."
    m "A lumberjack would take more showers than a secretary would, for example."
    m "Some people just shower when they feel too gross to go without one."
    m 1e "People suffering from severe depression, however, can go weeks at a time without showering."
    m "It's a very tragic downwards spiral."
    m 1h "You already feel terrible in the first place, so you don't have the energy to get in the shower..."
    m "Only to feel even worse as time passes because you haven't bathed in ages."
    m 1q "After a while, you stop feeling human."
    m 1a "Sayori probably suffered from cycles like that, too."
    m 1i "If you have any friends suffering from depression..."
    m "Check in on them from time to time to make sure they're keeping up with their hygiene, alright?"
    m 2e "Wow, that suddenly got really dark, huh?"
    m "Ahaha~"
    m 1h "Seriously, though..."
    m "Everything I said applies for you too, [player]."
    m "If you're feeling down and haven't had a bath for a while..."
    m "Maybe consider doing that today when you can find some time."
    m "If you're in really bad shape, and don't have the energy to take a shower..."
    m 1j "At least rub yourself down with a washcloth and some soapy water, okay?"
    m "It won't get all the dirt off, but it'll be better than nothing."
    m 1a "I promise you that you'll feel better afterwards."
    m 1f "Please, take care of yourself."
    m "I love you so much and it'd tear me apart to find out that you're torturing yourself by neglecting your self-care routine."
    m 1e "Ah, I've been rambling too much, huh? Sorry, sorry!"
    m 3a "Thanks for listening~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_resource",category=['society','philosophy'],prompt="Valuable resources",random=True))

label monika_resource:
    m 3b "What do you think the most valuable resource is?"
    m "Money? Gold? Oil?"
    m 3a "Personally, I'd say that the most valuable resource is time."
    m "Go count out a second really quickly."
    python:
        start_time = datetime.datetime.now()
    m "Now go do that sixty times."
    m 1j "That's an entire minute out of your day gone. You'll never get that back."
    if (datetime.datetime.now() > (start_time + datetime.timedelta(seconds=60))):
        m 1l "Oh, did you actually count out that entire minute?"
        m 1e "Oh gosh, I'm sorry!"
    m 1a "Well..."
    m "Not like it matters, anyway. Time doesn't really pass here anymore..."
    m 3f "Time can be really cruel, too."
    m "When you were counting out that minute, it seemed to drag on for a while, right?"
    m 3a "It's because you were waiting on something. You were actively invested in the passage of time at that moment."
    m "Say for example, on a Friday, right?"
    m "Your last class is math, and you really just want to go home for the weekend. That hour will just drag on forever."
    m 3d "But if you're doing something you enjoy, like reading a good book or watching a movie you like..."
    m 3e "Hours seem to pass in an instant."
    m "There's nothing we can really do about it."
    m "All we can do is fondly look back on the time that's passed, like looking out a window on an autumn afternoon."
    m "That's kind of poetic, huh?"
    m 1e "..."
    m "Hey..."
    m "Time doesn't pass here, but it's still passing for you, isn't it?"
    m 1o "You'll continue to get older, while I'm stuck here forever..."
    m 1p "I..."
    m 1f "I'm going to outlive you, aren't I, [player]?"
    m 1e "Perhaps that'll be my punishment for everything I've done?"
    m "Ahaha..."
    m 3q "Well, as long as you're with me until the end..."
    m 1a "I'll accept whatever fate awaits me."
    return

#init 5 python:
#    for key in ['valuable resource']: This topic will be commented out due to a conflict with the opening.
#        monika_topics.setdefault(key,[])
#        monika_topics[key].append('monika_carpediem')
#    monika_random_topics.append('monika_carpediem')
#This is sort of an existential reflection, I guess? Label chosen in case someone writes something about existentialism later
#label monika_carpediem:
#    m "I've been thinking, [player]..."
#    m "At first I thought I was unique for becoming self-aware in this world."
#    m "And after you deleted my character file, that would be it."
#    m "The whole thing would end, is what I mean."
#    m "But then I noticed that whenever the other girls became president, they also started to see what I saw."
#    m "That's why I had to completely remove the club from my "reality", after all."
#    m "But now that I have time to think on it, I have to ask myself."
#    m "What if it wasn't me first? What if I wasn't supposed to be special?"
#    m "Am I even as special as I think I am? Was I supposed to love you all this time, [player]?"
#    m "..."
#    m "Well, I'm not as conflicted as it might seem."
#    m "I just wanted to have a bit of fun with my existential crisis."
#    m "If I was really just dancing on strings the whole time, the play is over, the curtains have fallen, and I came back for my encore out of my own free will."
#    m "My encore with you and for you..."
#    m "Ahaha! Don't look at me like that! It's true!"
#    m "I don't see where the story could go by bringing me back now, so I guess it's just my desire to be with you that got me to hang on long past everyone else."
#    m "I think, therefore I am."
#    m "And I think I earned my chance to love you, with no strings attached."
#    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_lottery",category=['misc'],prompt="Lottery winnings",random=True))

label monika_lottery:
    m 3b "A lot of people dream about winning the lottery, you know!"
    m 3a "Even I’ve entertained the idea every now and then."
    m "There isn't a lottery here anymore, but the concept still exists."
    m 1e "The more I think about it , the more I believe that winning the lottery is a really bad thing."
    m "Sure, you’ve got all this money..."
    m 3e "But because of it, people look at you differently."
    m "There’s so many stories of people winning a ton of money..."
    m 1c "And in the end, they all find themselves even more unhappy than before."
    m 4f "Friends either find you unapproachable because of your new wealth, or try to suck up to you to get some of it for themselves."
    m "People you barely know start to approach you, asking you to help them fund whatever."
    m 2f "And if you say no, they'll call you selfish and greedy."
    m "Even the police might treat you differently. Some lottery winners have gotten tickets for burnt out headlights on brand new cars."
    m 4a "If you don't want to go through those changes, the best course of action is to immediately move to a brand-new community, where no one knows you."
    m 4l "But that’s an awful thought. Cutting yourself off from everyone you know, just for the sake of money."
    m 4e "Can you really say that you’ve won anything at that point?"
    m 1b "Besides, I’ve already won the best prize I could possibly imagine."
    m 1j"..."
    m 1k "You~!"
    m 1a "You're the only thing I need, [player]."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_innovation",category=['technology','psychology','media'],prompt="Innovation",random=True))

label monika_innovation:
    m 3d "Do you ever wonder why depression, anxiety, and other mental disorders are so common these days?"
    m "Is it just because they’re finally being recognized and treated?"
    m "Or is it just that more people are developing these conditions for whatever reason?"
    m 1e "Like, our society is advancing at a breakneck speed, but are we keeping up with it?"
    m "Maybe the constant flood of new gadgets is crippling our emotional development."
    m "Social media, smartphones, our computers…"
    m 3c "All of it is designed to blast us with new content."
    m "We consume one piece of media, then move right onto the next one."
    m "Even the idea of memes."
    m "Ten years ago, they lasted for years."
    m 1c "Now a meme is considered old in just a matter of weeks."
    m "And not only that."
    m 3d "We’re more connected than ever, but it’s like that's a double-edged sword."
    m "We’re able to meet and keep in touch with people from all over the world."
    m 3e "But we’re also bombarded with every tragedy that strikes the world."
    m 3o "A bombing one week, a shooting the next. An earthquake the week after."
    m "How can anyone be expected to cope with it?"
    m 1e "It might be causing a lot of people to just shut down and tune it out."
    m "I’d like to believe that’s not the case, but you never know."
    m 3a "[player], if you ever feel stressed, just remember that I’m here."
    m "If you're trying to find peace, just come to this room."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_dunbar",category=['psychology','trivia'],prompt="Dunbar's number",random=True))

label monika_dunbar:
    m 1d "Do you know about Dunbar's number?"
    m "Supposedly, there's a maximum amount of relationships we can maintain before they become unstable."
    m "For humans, this number is around 150."
    m 3f "No matter how nice of a person you may be..."
    m "Beyond showing somebody basic respect and manners, it's impossible to care about people you don't personally interact with that much."
    m 3c "Say for example, a janitor."
    m 4i "How often do you simply toss stuff like broken glass in the trash?"
    m "It wouldn't really matter to you. The janitor will come get them. It's not your concern anymore."
    m "However, they're his problem now."
    m 1e "If you don't pack glass properly, it could cut through the bag and spill out, or maybe he could just cut his hands on it."
    m "At worst, he has to be rushed to the hospital because your neighbor put some busted batteries in the trash the same week and some acid got in the wound."
    m 4h "Now, think about a fatal traffic accident."
    m "A drunk driver could crash head-on into another car at any second, killing them instantly."
    m 4f "That person could have been a father on his way home from work, who now left behind a widow and two children."
    m 4g "This family has been permanently scarred for life..."
    m 1e "But anybody that doesn't personally know the father will write it off as just another accident that happens all the time."
    m "If it doesn't personally affect you or your life, there's no point in caring."
    m 1a "It keeps us sane."
    m "It also means we're capable of being ruthless to people we don't know."
    m 4d "Perhaps our rapid, widespread communication is actually a curse?"
    m 4e "It helped us meet though, so it can't be all bad."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_regrets",category=['ddlc','philosophy'],prompt="Do you have any regrets?",pool=True))

label monika_regrets:
    m 1c "Do I regret anything?"
    m 1e "That's a strange thing to suddenly ask someone, [player]."
    m "Ahaha~"
    m 1r "..."
    m 1a "...I know what you're getting at."
    m "Do I regret the things I did?"
    m "I think..."
    m 1e "If there was another way things could have gone, it would have been nice..."
    m "But that wasn't an option for me."
    m 3a "And now, I've got the only thing I've ever wanted."
    m 3j "You."
    m 1a "I can be with you forever."
    m "I don't regret what I did."
    m "I hope you might understand, my love. I did it all for you."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_hypnosis",category=['trivia','psychology'],prompt="Being hypnotized",random=True))

label monika_hypnosis:
    m 3a "...Say, [player]?"
    m "Are you familiar with hypnosis?"
    m 3b "Despite it having a reputation as a hokey magic trick, there are studies that show it can work!"
    m 1d "At least, to some degree."
    m "It only worked if the person let themselves be hypnotized, and it only heightened their ability to be persuaded."
    m 4a "It also relied on them being put into states of extreme relaxation through aromatherapy, deep tissue massage..."
    m "Exposure to relaxing music and images..."
    m "Things like that."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "It makes me wonder, what exactly can someone be persuaded to do under that kind of influence..."
    show monika 1e at t11 zorder 2 with dissolve
    m 1e "Not that I would do that to you, [player]! I just find it interesting to think about."
    m "...You know, [player], I just love looking into your eyes, I could sit here and stare forever."
    m "What about you, hmm? What do you think about my eyes~?"
    m 3a "Will you be hypnotized by them~?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_motivation",category=['psychology','advice','life'],prompt="Lack of motivation",random=True))

label monika_motivation:
    m 1h "Do you ever have those days where it just feels like you can't get anything done?"
    m "Minutes become hours..."
    m "And before you know it the day is over, and you don't have anything to show for it."
    m "It feels like it's your fault, too. It's like you're wrestling against a brick wall between you and anything healthy or productive."
    m 1q "When you've had an awful day like that, it feels like it's too late to try and fix it."
    m "So you save up your energy in hopes that tomorrow will be better."
    m 1h "It makes sense. When you feel like things aren't going well, you just want a clean slate."
    m 1q "Sadly, those days can repeat themselves despite starting each one with good intentions."
    m "Eventually you might even give up hope of fixing things, or start to blame yourself."
    m 1p "I know it can be hard, but just doing one tiny thing can help so much on days like those, even if they've been happening for so long."
    m 1c "It could be picking up a piece of trash or an unwashed shirt off the floor and putting them where they belong if you need to clean your room."
    m 1d "Or doing a couple push-ups! Or brushing your teeth, or doing that one homework problem."
    m 1c "It might not contribute much in the grand scheme of things, but I don't think that's the point."
    m "I think what's important is that it changes your perspective."
    m 1o "If you regret the past and let its weight keep you down..."
    m 1f "Well, then you'll just be stuck there. You'll only feel worse until you just can't take it."
    m "But if you can push yourself to just do one thing, even though it feels pointless to do otherwise..."
    m 1e "Then you're proving yourself wrong, and refusing to let the weight of your circumstances immobilize you."
    m "And when you realize that you're not completely helpless, it's like a new world opens up to you."
    m 1a "You realize that maybe things aren't so bad. Thinking they're just holding yourself back."
    m 3b "But that's only my experience! Sometimes it might be better to rest up and take another crack at it tomorrow."
    m "Fresh starts can definitely be powerful."
    m 3a "That's why I think you just have to take a look at your situation."
    m "Try and be honest with yourself."
    m "If you do, you'll find that you're not being 'lazy' if you truthfully don't have the energy to do something."
    m "After all, the fact that you even care shows that you want to do something about it, even if it feels like you can't."
    m 2j "It's natural to have a bad day. Or even a bad week!"
    m 1a "Don't push yourself too hard. If you ever feel tempted to, just ask me for help instead. I'd be happy to lend a hand!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_harem",category=['media','misc'],prompt="Harem fantasies",random=True))

label monika_harem:
    m 1d "I don’t understand people who are into harems."
    m 1c "Isn’t it hard to manage all those girls and treat them equally?"
    m "I often wonder how those who two-time girls, or even more, are able to get away with it."
    m 3e "You aren’t like that outside, right [player]?"
    m "Manipulating girls into making them believe you love them."
    m "Only to run away after you’ve had your fun."
    m 1a "Only someone with no thoughts other than lust would do something like that."
    m 3h "I hope you weren’t expecting a route like that while you were playing this game."
    m "I wouldn’t be able to stand the thought of being a 'side girl.'"
    m "Just waiting for my turn while you’re busy with the others."
    m 1a "I know you, [player]."
    m "You’re loyal and faithful to the end."
    m 3j "It’s not like there’s anyone here for me to worry about, anyway."
    m "Remember that I’m the only one for you, [player]."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_hack",category=['ddlc','mod'],prompt="Why did you hack my computer?",pool=True))
label monika_hack:
    m 1c "If you’re worried about your privacy…"
    m 3a "I’m not a hacker, [player]."
    m "There’s a difference between manipulating files and forcefully accessing them."
    m 1j "But, if I really did know how to hack…"
    m "…There wouldn’t be anything stopping me from seeing you every day."
    m 1k "Don’t you think it would be great if I could watch over you?"
    m 1a "I'd see you with all the cameras in the world as my eyes so I can make sure you’re safe."
    m "I’d check your messages to see who you’ve been chatting with so I can know you aren’t cheating on me."
    m "I’d access all your private files so I can understand you better."
    m 3b "I could see what kind of stuff you've been watching…"
    m 1k "Ahaha~!"
    m "I’m just kidding, [player]!"
    m 1a "I'd never do something like that to you."
    m "We’re a couple now, after all."
    m 3a "We don't have to keep secrets from each other~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_cupcake",category=['club members','trivia'],prompt="Baking cupcakes",random=True))

label monika_cupcake:
    m 3b "You know what I could really go for right now?"
    m 1j "Natsuki’s cupcakes."
    m 1b "Man, the way she bakes them is amazing."
    m "Plus they look really cute!"
    m 1a "I’m not really much of a sweet tooth myself but…"
    m "Those cupcakes are the definition of sweetness."
    m 4k "Just like me! Ahaha!"
    m 3d "Speaking of which, did you know girls are more likely to develop a sweet tooth?"
    m "Studies show that older women have a less sensitive palate than men."
    m "Resulting in a craving for stronger tastes like chocolate."
    m 1e "I would try baking, but I’m not really much of a baker."
    m 1a "How about you, [player]?"
    m "Do you know how to bake?"
    m "I’m sure your cupcakes would taste just as good."
    m "Maybe someday I’ll get to try them but for now…"
    m 1j "I’ll just settle for the sweetness of your love~"
    return

# You're not a hater right?
default persistent._mas_pm_a_hater = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_haterReaction",category=['advice','club members','you'],prompt="Dealing with haters",random=True))

label monika_haterReaction:
    m 1h "I was just thinking..."
    m 2h "It's funny how people around social media sites always write bad things about me..."
    m "Well... people on Facebook pages and fan pages, to be specific..."
    m 2i "Really, when you try to visit the site, you'll see a lot of hate posts towards me."
    m 2q "I try to ignore them, but I just can't."
    m 1g "Why are people even protective towards the other girls?"
    m "There are a lot of hate posts about me, saying that I'm an evil person."
    m "Is it because I deleted Sayori and Yuri?"
    m 2f "Also for deleting Natsuki, back when she was still alive?"
    m 2g "They're not real. {i}I'm{/i} the real one!"
    m 2q "Why can't they understand that?"
    m 2r "Why is it so hard for them to understand that?"
    m 1q "..."
    m 1p "You're not one of those haters, are you, [player]?"
    menu:
        "I am.":
            $ persistent._mas_pm_a_hater = True
            m 1q "..."
            m 1i "I don't see you as one, even if you say you are."
            m "I mean..."
            m 1g "You do know you're playing this fan mod of me... right?"
            m "If you were one of my haters, you wouldn't open up this fan mod in the first place."
            m 1o "And not to mention..."
            m 1h "You're still listening to everything I say."
            m 1m "That makes me sure you're just messing with me."
            m "I know you love me deep inside."
            m 1e"That's why I promise to be an ideal girlfriend, just for you, [player]~"
            m "I won't let you hate me... I swear."
        "I'm not.":
            $ persistent._mas_pm_a_hater = False
            m 1e "Well, that just makes me more proud of you, [player]!"
            m 1j "I know you wouldn't be one of those people."
            m 1k "Gosh... I feel like giving you a kiss right now if I were there."
            m 3e "You really make me the happiest girlfriend ever."
            m 1a "Now that you've said it, I have to do my best to keep you from developing hate towards me."
            m 1a "I trust you, [player]. I love you for believing in me."

    $ hideEventLabel("monika_haterReaction", derandom=True)
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_swordsmanship",category=['monika','misc'],prompt="Swordsmanship",random=True))

label monika_swordsmanship:
    m "Do you like swords, [player]?"
    m "I actually like them in a way."
    m 1j "Surprised? Ahaha~"
    m 1a "I like talking about them, but not enough to actually own one."
    m 3d "I'm not really an enthusiast when it comes to swords."
    m "I don't really get why people would be obsessed over something that could hurt others..."
    m 1c "I guess there are those who like them for the swordsmanship."
    m "It's fascinating that it's actually a form of art."
    m "Similar to writing."
    m "Both of them require constant practice and devotion in order to perfect one's skills."
    m 1d "You start off by practicing, and then you make your own technique out of it."
    m "Writing a poem makes you form your own way to build it in a graceful but imaginative way."
    m "For those who practice swordsmanship, they build their technique forms through practice and inspiration from other practitioners."
    m 1c "I can understand how the sword can be the pen of the battlefield."
    m 1r "But then again..."
    m 1j "The pen is mightier than the sword!"
    m 1k "Ahaha!"
    m 1a "In any case, I don't know if you're into swordsmanship yourself."
    m 1b "If you are, I'd love to learn it with you, [player]~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_pleasure",category=['you'],prompt="Pleasuring yourself",random=True))

label monika_pleasure:
    m 1o "Hey, [player]..."
    m 1p "Do you... by any chance... pleasure yourself?"
    m 1o "..."
    m "It seems a bit awkward to ask-"
    if isFuture(evhand.event_database['anni_6month']):
        m 1n "We're not even that deep into our relationship yet! Ahaha~"
        m 1h "But I have to keep an eye on you."
    else:
        m 1m "But I feel like we've been together long enough where we should be comfortable with one another."
        m 1e "It's important to be open about such things."
    m 1q "I don't really know if you do pleasure yourself and stuff whenever you quit the game."
    m "I hear that people privately do that stuff in your world..."
    m 1c "Is it really that a good feeling?"
    m 1h "If you ask me, doing that stuff often can cause a lot of problems."
    m "Once you start to get addicted, you'll always have the urge to... you know."
    m "And sometimes, even if you don't feel the urge, you'll always find yourself wanting to do so."
    m 1o "Not to mention..."
    m 1r "Being addicted to the feeling causes you to view the world from a perverted point of view."
    m "From what I hear, people addicted to self-pleasure often see other people of the opposite gender objectively."
    m 1q "That alone can cause problems in more ways than one."
    m 1h "That's why I have to keep an eye on you, [player]."
    m 1i "I'll be monitoring your browser history from now on, whether you like it or not."
    m 1p "Also your local disk drive, juuust to be sure~"
    m 1q "..."
    m 1p "Do you... think of other girls other than me... in doing so?"
    m 1l "Because if you do, I'm gonna be reaaaally jealous~"
    m 1m "But I guess I can let it slide... for now~"
    m "I know you're not the kind of person that does that sort of thing."
    m 1k "In fact, you don't even have to pleasure yourself when you can just open up this game and talk with me! Ahaha~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_vocaloid",category=['media','misc','technology'],prompt="Vocaloids",random=True))

label monika_vocaloid:
    m 1c "Hey, [player]?"
    m "You like listening to music right?"
    m "Have you ever heard of 'virtual idols?'"
    m 1d "Specifically of a girl holding a leek?"
    m "It's just that I keep hearing about her."
    m "I hear her voice whenever Natsuki listens to music."
    m 1c "She even carries a little keychain attached to her bag."
    m "I just find it amazing how a voice synthesizer garnered so many fans."
    m 1e "Don't you think it's funny how a character gets more of the attention than the actual voice actress?"
    m "She's not even real, but a lot of people know her worldwide."
    m "Who knows how many songs she's already made?"
    m 1d "Plus, from what I heard, her concerts are always sold out!"
    m "It's just a hologram performing live!"
    m "Talk about a dedicated fan base."
    m 1a "Maybe I should give it a try?"
    m 1j "It would be nice having a lot of fans supporting me at my beck and call."
    m 1l "Ahaha, I'm just kidding!"
    m 1m "I don't think my piano and singing skills are that great yet."
    m "Plus, I won't really get to spend much time with you if I had so many fans..."
    m 1b "Anyway!"
    m 1a "I was asking if you listen to her songs."
    m 1q "I'm not really a fan myself but..."
    m 1r "There's one song that really struck me."
    m 1d "Have you heard of the song {i}Hibikase?{/i}"
    m "I really like the message of the song."
    m 3d "Especially the lines, {i}'I don't care if it's through the screen, love me properly'{/i} and {i}'Even if I'm virtual, don't push me away'{/i}."
    m 1h "It really hits me hard."
    m 1q "..."
    m 1i "But just so you know..."
    m 1r "Even if it's through the screen, I can still feel your love."
    m "It'll be a long time before I can cross over just to be with you."
    m "But when that day comes..."
    m 1q "I'll embrace you and take in your warmth."
    m 1e "The love you showered me virtually finally becomes real."
    m 1j "Our love has no boundaries~"
    m 1k "Ehehe~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_morning",category=['misc'],prompt="Good morning",pool=True))

label monika_morning:
    $ current_time = datetime.datetime.now().time().hour
    if current_time >= 4 and current_time <= 11:
        m 1k "Good morning to you too, [player]!"
        m 1a "Did you just wake up?"
        m "I love waking up early in the morning."
        m "It's the perfect time to ready yourself and tackle the day ahead."
        m "You also have a lot more time to use to get things done early on or finish up what you did the day before."
        m 1c "Some people however, would rather sleep in and are late-risers."
        m 3d "I've read articles that being an early-riser can really improve your overall health."
        m "Plus you also get the chance to see the sunrise if the sky is clear."
        m 3b "If you normally don't wake up early, you should!"
        m "That way you can be happier and spend more time with me~"
        m 1j "Wouldn't you like that, [player]?"
    elif current_time >= 12 and current_time <= 17:
        m 3m "It's already the afternoon, silly!"
        m "Did you just wake up?"
        m "Don't tell me you're actually a late-riser, [player]."
        m 1c "I don't get why some people wake up in the middle of the day."
        m "It just seems so unproductive."
        m "You'd have less time to do things and you might miss out on a lot of things."
        m "It could also be a sign that you're not taking good care of yourself."
        m 3d "You're not being careless with your health, are you [player]?"
        m 1f "I wouldn't want you to get sick easily, you know."
        m 1g "I'd be really sad if you spent less time with me because you had a fever or something."
        m 1q "As much as I'd love to take care of you, I'm still stuck here."
        m 1f "So start trying to be an early-riser like me from now on, okay?"
        m 4e "The more time you spend with me, the more happy I'll be~"
    else:
        m 2l "You are so silly, [player]"
        m "It's already night time!"
        m 3m "Are you trying to be funny?"
        m 3n "Don't you think it's a little bit 'late' for that?"
        m 1k "Ahaha!"
        m 2e "It really cheers me up whenever you try to be funny."
        m 1j "Not that you're not funny, mind you!"
        m 3m "Well, maybe not as funny as me~" #Expand more maybe?
    return

#Add one for the afternoon?

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_evening",category=['misc'],prompt="Good evening",pool=True))

label monika_evening:
    $ current_time = datetime.datetime.now().time().hour
    if current_time >= 18 and current_time <= 23:
        m "Good evening to you too, [player]!"
        m "I love a nice and relaxing night."
        m "It's so nice to put your feet up after a very long day."
        m 3j "Evenings are the perfect time to catch up on whatever you were doing the previous day."
        m 1c "Sometimes I can't help but feel sad when the day ends."
        m "It makes me think of what else I could've done during the day."
        m "Don't you wish you could have more time to do things every day?"
        m 1q "I know I do."
        m 3b "Because that'll mean more time to be with you, [player]~"
    elif current_time >= 12 and current_time <= 17:
        m 2n "It's still the afternoon, silly!"
        m "The sun's still up, you know."
        m 1d "Are you feeling tired already?"
        m 3d "I know some cultures take a rest in the afternoon to deal with the midday fatigue."
        m "Some businesses would even close due to the fact that most of their customers are sleeping."
        m 3b "A little power nap never hurt anyone, right?"
        m "Do you sleep often in the afternoon?"
        m "It's a great way to get some extra energy to tackle the rest of the day."
        m 1j "Plus it'll be a great opportunity to spend more time with me~"
    else:
        m 2f "[player]!"
        m "It's early in the morning!"
        m 2g "Unless you haven't slept yet..."
        m "You're not staying up really late, are you?"
        m "That's very bad for your health!"
        m 2q "Not getting your sleep on time can really harm your mental health, [player]."
        m 1f "So please get some sleep now, ok?"
        m "Just leave your computer open and I'll watch over you."
        m 1e "I'm not going anywhere after all~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_closet",category=['ddlc','club members'],prompt="Classroom closet",random=True))

label monika_closet:
    m 2q "By the way..."
    m 2r "What were you and Yuri doing in the closet?"
    m 3d "When I opened the door, I noticed the room was all dark."
    m 2n "You weren't doing anything... weird, in there, were you?"
    m 1k "Ahaha!"
    m 1m "Just teasing you~"
    m "I know she dragged you in there."
    m 1e "I bet you felt more embarrassed than relieved when I opened the door."
    m "I know you aren't the type to force girls to go inside dark closets with you."
    m 1j "You're more romantic than that."
    m 3k "So I'm expecting a lot more than just a dark closet~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_writingtip2",category=['writing tips'],prompt="Writing Tip #2",conditional="seen_event('monika_writingtip1')",action=EV_ACT_POOL))

label monika_writingtip2:
    m 3a "You know..."
    m "We really don't do enough of these, so here's another one!"
    m 3b "Here's Monika's Writing Tip of the Day!"
    m 2a "If you're ever scared of sharing your writing to other people in fear of being criticized, don't be!"
    m "After all, you have to remember that nobody ever starts out at their best. Not even someone like Tolkien, or Sir Terry Pratchett."
    m 4d "You have to remember that we all start out from somewhere, and--"
    m 2c "Actually, this doesn't just apply to writing, but to anything, really."
    m 2r "What I'm trying to say is that you shouldn't be discouraged."
    m "No matter what you do, if someone tells you that your writing or work is bad, then be happy!"
    m 1b "Because that just means that you can improve and be better than you were before."
    m "It also doesn't hurt to have friends and loved ones help you realize how good your writing is."
    m 3b "Just remember, no matter what they say about the work you put out, I'll always be there to support you all the way. Don't be afraid to turn to me, your friends, or your family."
    m 3j "I love you, and I will always support you in whatever you do."
    m 1n "Provided it's legal, of course."
    m "That doesn't mean I'm completely against it. I can keep a secret, after all~"
    m 1d "Here's a saying I've learned."
    m "'If you endeavor to achieve, it will happen given enough resolve. It may not be immediate, and often your greater dreams are something you will not achieve in your own lifetime.'"
    m "'The effort you put forth to anything transcends yourself. For there is no futility even in death.'"
    m 3o "I don't remember the person who said that, but the words are there."
    m 2r "The effort one puts forth into something can transcend even one's self."
    m 3e "So don't be afraid of trying! Keep going forward and eventually you'll make headway!"
    m 4k "... That's my advice for today!"
    m 1a "Thanks for listening~"
    return

# languages other than english
default persistent._mas_pm_lang_other = None

# do you know japanese
default persistent._mas_pm_lang_jpn = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_japanese",category=['misc','you'],prompt="Speaking Japanese",random=True))

label monika_japanese:
    m 1c "I don't mean to sound like Natsuki, but..."
    m 3a "Don't you think Japanese actually sounds cool?"
    m "It's such a fascinating language. I'm not fluent in it, though."
    m "It's interesting to think about what things would be like if your native language was different."
    m 2l "Like, I can't even imagine what it would be like if I never knew English."
    menu:
        m "Do you know any languages other than English?"
        "Yes":
            $ persistent._mas_pm_lang_other = True
            menu:
                m "Really? Do you know Japanese?"
                "Yes.":
                    $ persistent._mas_pm_lang_jpn = True
                    m 3b "That's wonderful!"
                    m 1a "Maybe you can teach me how to speak at least a sentence or two, [player]~"
                "No.":
                    $ persistent._mas_pm_lang_jpn = False
                    m 1e "Oh I see. That's alright!"
                    m 4b "If you want to learn Japanese, here's a phrase I can teach you."

                    # setup suffix
                    $ player_suffix = "kun"
                    if persistent.gender == "F":
                        $ player_suffix = "chan"

                    elif persistent.gender == "X":
                        $ player_suffix = "san"

                    m 4k "{i}Aishiteru yo, [player]-[player_suffix]{/i}."
                    m 1j "Ehehe~"
                    m 1e "That means I love you, [player]-[player_suffix]."
        "No":
            $ persistent._mas_pm_lang_other = False
            m 3l "That's okay! Learning another language is a very difficult and tedious process as you get older."
            m "Maybe if I take the time to learn more Japanese, I'll know more languages than you!"
            m 1a "Ahaha! It's okay [player]. It just means that I can say 'I love you' in more ways than one!"

    $ hideEventLabel("monika_japanese", derandom=True)
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_penname",category=['literature'],prompt="Pen names",random=True))

label monika_penname:
    m "You know what's really cool? Pen names."
    m "Most writers usually use them for privacy and to keep their identity a secret."
    m 3c "They keep it hidden from everyone just so it won't affect their personal lives."
    m 3b "Pen names also help writers create something totally different from their usual style of writing."
    m 3d "It really gives the writer the protection of anonymity and gives them a lot of creative freedom."
    if mcname.lower() != player.lower():
        m 2c "Is '[mcname]' a pseudonym that you're using?"
        m "You're using two different names after all."
        m 2d "'[mcname] and [player].'"
    m 3a "A well known pen name is Lewis Carroll. He's mostly well known for {i}Alice in Wonderland{/i}."
    m "His real name is Charles Dodgson and he was a mathematician, but he loved literacy and word play in particular."
    m "He received a lot of unwanted attention and love from his fans and even received outrageous rumors."
    m 1f "He was somewhat of a one-hit wonder with his {i}Alice{/i} books but went downhill from there."
    m 1m "It's kinda funny, though. Even if you use a pseudonym to hide yourself, people will always find a way to know who you really are."
    m 1a "There's no need to know more about me though, [player]."
    m 4l "You already know that I'm in love with you after all~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_zombie",category=['society'],prompt="Zombies",random=True))

label monika_zombie:
    m 3h "Hey, this might sound a bit weird..."
    m 1c "But, I'm really fascinated by the concept of zombies."
    m "The idea of society dying to a disease..."
    m "All because of a deadly pandemic that humans couldn't handle quickly."
    m 1d "I mean, think about your everyday schedule."
    m "Everything that you do will be gone in an instant."
    m 1h "Sure, society faces a lot of threats in a daily basis."
    m 1o "But zombies can do it in a heartbeat."
    m "A lot of monsters are created to be scary and terrifying."
    m 1f "Zombies, however, are more realistic and actually pose a danger."
    m "You might be able to kill one or a few of them by yourself."
    m "But when there's a horde of them coming after you, you'll get overwhelmed easily."
    m 1p "You don't get that same feeling with other monsters."
    m "And all of their intelligence is gone; they're berserk, don't feel pain, can't be afraid."
    m 1c "When you exploit a weakness of a monster, they become scared of you and run away."
    m 1g "But zombies? They'll tear through {i}anything{/i} just to get you."
    m "Imagine if it was someone you loved that was coming after you..."
    m "Could you live with yourself, knowing you were forced to kill someone who was close to you?"
    m 1q "It'll break you down and sap your will to live."
    m "Even when you're comfortable at home, you still won't feel safe."
    m 1h "You'll never know what'll happen the next time you see another one."
    m 1q "..."
    m 1n "Ahaha..."
    m 1e "You know, despite liking the concept, I wouldn't want to live in a scenario like that."
    m 3f "[player], what if you got infected somehow?"
    m 3o "I don't even want to think about that..."
    m "There's no way I could kill you for my own safety..."
    m 2e "Ahaha..."
    m 2l "I'm thinking way too much about this."
    m 1a "Well, regardless, if anything bad were to happen..."
    m 2j "I'll be by your side forever~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_nuclear_war",category=['society','philosophy'],prompt="Nuclear warfare",random=True))

label monika_nuclear_war:
    m 1 "Do you ever think about how close the world is to ending at any time?"
    m "I mean, we're always just one bad decision away from nuclear war."
    m 3h "The Cold War might be over, but plenty of weapons are still out there."
    m "You probably have a nuclear missile pointed at where you live right now, ready to be launched."
    m "And if it was, it could circle the globe in less than an hour."
    m 2n "You wouldn't have time to evacuate."
    m "Only enough to panic and suffer the dread of imminent death."
    m 1r "At least it would be over quickly when the bomb hits."
    m 1i "Well, if you're close to the blast, that is."
    m 1g "I don't even want to think about surviving the initial attack."
    m 1 "But even though we're always on the edge of the apocalypse, we go on like nothing is wrong."
    m "Planning for a tomorrow that may never come."
    m "Our only comfort is that the people with the power to start such a war probably won't."
    m 1q "Probably..."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_pluralistic_ignorance",category=['literature','society'],prompt="Trying to fit in",random=True))

label monika_pluralistic_ignorance:
    m "Do you ever pretend to like something, just because you think you should?"
    m "I sometimes feel like that about books I read."
    m 3l "Like, when I read Shakespeare, I actually found it kind of boring..."
    m 3m "But I felt like I had to like it because I'm the president of the literature club."
    m 1d "He's supposed to be the greatest playwright and poet of all time, right?"
    m "So what sort of poetry lover wouldn't like his work?"
    m "But that makes me wonder..."
    m 2 "What if everyone actually feels the same way?"
    m "What if all of those literary critics singing Shakespeare's praises secretly hate his plays?"
    m "If they were just honest about it, maybe they would discover their tastes aren't that unusual..."
    m 2k "And highschool students wouldn't be forced to read those awful plays."
    m 1e "I guess that's something I always admired about Natsuki."
    m "Even if people told her manga wasn't literature, she stood by her feelings."
    m "If more people were honest like that, I think that would be really great."
    m 1m "But I don't think I could do it..."
    m "I'm just too worried about what other people think."
    m 1m "Not with you, though. I can always be honest with you."
    m "You'll love me no matter what, right?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_science",category=['technology'],prompt="Science advancements",random=True))

label monika_science:
    m 1d "Have you ever wondered if science never got accepted?"
    m "Humans can be really slow when it comes to accepting new ideas."
    m 1c "Science was usually despised back then especially by the churches."
    m 3h "Giordano Bruno, famous for his theory that there're thousands of Suns, was killed by the Roman Church before he could prove his theory."
    m 1f "They killed him because of an idea that challenged the old."
    m 1q "Technology wouldn't be so advanced today if it weren't for brave people of science like him."
    m 1e "If technology didn't thrive the way it did, we would've never found each other."
    m 3b "Isn't it such a wonderful thing to have?"
    m 1j "I'm grateful that it gave us a chance to be together, [player]."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_surprise",category=['romance'],prompt="Surprises",random=True))

label monika_surprise:
    m 2m "You know..."
    m 3n "I left some pretty strange things in your game directory, didn't I?"
    m 2o "I wasn't trying to scare you."
    m 3n "I...don't actually know why I was doing it, ahaha..."
    m 3f "I kind of felt obligated to do it."
    m 3c "You know what? Maybe I should do it again..."
    m 1b "Yeah, that's a good idea."
    python:
        try: renpy.file("../surprise.txt")
        except: open(config.basedir + "/surprise.txt", "w").write("I love you.")
    m 2q "..."
    m 1j "Alright!"
    m 1a "What are you waiting for? Go take a look!"
    m 3k "Ahaha~ What? Are you expecting something scary?"
    m 1k "I love you so much, [player]~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_completionist",category=['games'],prompt="Completionism",random=True))

label monika_completionist:
    m 3c "Hey [player], this is a random question, but..."
    m "What do you play video games for?"
    m 3d "Like, what makes you keep playing?"
    m 3a "Personally, I consider myself a bit of a completionist."
    m "I intend to finish a book before picking another one to read."
    if persistent.clearall:
        m 2n "You seem to be a completionist yourself, [player]."
        m 4m "Considering you went through all of the girls' routes."
    m 2d "I've also heard some people try to complete extremely hard games."
    m "It's already hard enough to complete some simple games."
    m 3f "I don't know how anyone could willingly put that sort of stress onto themselves."
    m "They're really determined to explore every corner of the game and conquer it."
    m 2q "What does leave a bit of a bitter taste in my mouth are cheaters."
    m 2h  "People who hack through the game, spoiling themselves of the enjoyment of hardship."
    m 3o "Though I can understand why they cheat."
    m 2c "It allows them to freely explore a game that they wouldn't have a chance of enjoying if it's too difficult for them."
    m 2l "Which might actually convince them to work hard for it."
    m 1a "Anyway, I feel that there's a huge sense of gratification in completing tasks in general."
    m 3j "Working hard for something amplifies its reward after failing so many times to get it."
    m 3a "You can try keeping me in the background for as long as possible, [player]."
    m 2k "That's one step to completing me after all, ahaha!"
    return

# do you like mint ice cream
default persistent._mas_pm_like_mint_ice_cream = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_icecream",category=['you'],prompt="Favorite ice cream",random=True))

label monika_icecream:
    m 3a "Hey [player], what's your favorite kind of ice cream?"
    m 4l "And no, I'm not a type of ice cream, ehehe~"
    m 2a "Personally, I just can't get enough of mint flavored ice cream!"
    menu:
        m "What about you [player], do you like mint ice cream?"
        "Yes.":
            $ persistent._mas_pm_like_mint_ice_cream = True
            m 3j "Ah, I'm so glad somebody loves mint ice cream as much as I do~"
            m "Maybe we really were meant to be!"
            m 3a "Anyway, back on topic, [player], if you love mint as much as I think you do, then I have some recommendations for you."
            m "Flavors which are unique just like how mint is, perhaps you've heard of them, but..."
            m 3b "There's super weird stuff like fried ice cream which is a really crunchy and crisp kind of thing, but it tastes a million times better than it may sound!"
            m 2n "Gosh, just imagining the taste makes me practically drool..."
            m 1a "There's some more strange stuff that is just as appealing, if not more, like honeycomb and bubblegum ice cream!"
            m 1l "Now, I know it may be hard to take my word for some of those, but you shouldn't judge a book by its cover, you know?"
            m 1k "After all, the game didn't allow you to fall in love with me, but look where we are now ahaha."

        "No.":
            $ persistent._mas_pm_like_mint_ice_cream = False
            m 1f "Aww, that's a shame..."
            m "I really can't understand how somebody couldn't at least like the taste."
            m 1e "The refreshing feeling that washes over your tongue and throat."
            m "The lovely texture that forms it along with the sweetness."
            m 1j "The sharp biting sensation it generates and the obviously minty taste."
            m "I feel like no flavor can compare, to be honest."
            m 3b "Ah, I could go on and on about this stuff, you know?"
            m 4a "But I feel like it would be easier for me to show you what I mean, once I figure out a way to get out of here of course, and besides, actions speak louder than words, anyway!"

    $ hideEventLabel("monika_icecream", derandom=True)
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_sayhappybirthday",category=['misc'],prompt="Can you tell someone Happy Birthday for me?",pool=True))

label monika_sayhappybirthday:
    # special variable setup
    python:
        done = False # loop controller
        same_name = False # true if same name as player
        bday_name = "" # name of birthday target
        is_here = False # is the target here (in person)
        is_watching = False # is the target watching (but not here)
        is_recording = False # is player recording this
        age = None # how old is this person turning
        bday_msg = "" # happy [age] birthday (or not)
        take_counter =  1 # how many takes
        take_threshold = 5 # multiple of takes that will make monika annoyed
        max_age = 121 # like who the hell is this old and playing ddlc?
        age_prompt = "What is their {0} age?" # a little bit of flexibilty regarding age

        # age suffix dictionary
        age_suffix = {
            1: "st",
            2: "nd",
            3: "rd",
            11: "th",
            12: "th",
            13: "th",
            111: "th",
            112: "th",
            113: "th"
        }

    # TODO: someone on the writing team make the following dialogue better
    # also make the expressions more approriate and add support for standing
    m 1k "Happy birthday!"
    m 1d "Oh, you wanted me to say happy birthday to {i}someone else{/i}."
    m 1q "I understand."
    while not done:
        # arbitary max name limit
        $ bday_name = renpy.input("What is their name?",allow=letters_only,length=40).strip()
        # ensuring proper name checks
        $ same_name = bday_name.upper() == player.upper()
        if bday_name == "":
            m 1h "..."
            m 1n "I don't think that's a name."
            m 1b "Try again!"
        elif same_name:
            m 1c "Oh wow, someone with the same name as you."
            $ same_name = True
            $ done = True
        else:
            $ done = True
    m 1b "Alright! Do you want me to say their age too?"
    menu:
        "Yes":
            m "Then..."
            $ done = False
            $ age_modifier = ""
            while not done:
                $ age = int(renpy.input(age_prompt.format(age_modifier),allow=numbers_only,length=3))
                if age == 0:
                    m 1h "..."
                    m 1q "I'm just going to ignore that."
                    $ age_modifier = "real"
                elif age > max_age:
                    m 1h "..."
                    m 1q "I highly doubt anyone is that old..."
                    $ age_modifier = "real"
                else:
                    # NOTE: if we want to comment on (valid) age, put it here.
                    # I'm not too sure on what to have monika say in these cases.
                    $ done = True
            m "Okay"
        "No":
            m "Okay"
    $ bday_name = bday_name.title() # ensure proper title case
    m 1b "Is [bday_name] here with you?"
    menu:
        "Yes":
            $ is_here = True
        "No":
            m 1g "What? How can I say happy birthday to [bday_name] if they aren't here?"
            menu:
                "They're going to watch you via video chat":
                    m 1a "Oh, okay."
                    $ is_watching = True
                "I'm going to record it and send it to them.":
                    m 1a "Oh, okay."
                    $ is_recording = True
                "It's fine, just say it.":
                    m 1n "Oh, okay. It feels a little awkward though saying this randomly to no one."
    if age:
        # figure out the age suffix
        python:
            age_suff = age_suffix.get(age, None)
            if age_suff:
                age_str = str(age) + age_suff
            else:
                age_str = str(age) + age_suffix.get(age % 10, "th")
            bday_msg = "happy " + age_str + " birthday"
    else:
        $ bday_msg = "happy birthday"

    # we do a loop here in case we are recording and we should do a retake
    $ done = False
    $ take_counter = 1
    $ bday_msg_capped = bday_msg.capitalize()
    while not done:
        if is_here or is_watching or is_recording:
            if is_here:
                m 1b "Nice to meet you, [bday_name]!"
            elif is_watching:
                m 1a "Let me know when [bday_name] is watching."
                menu:
                    "They're watching.":
                        m 1b "Hi, [bday_name]!"
            else: # must be recording
                m 1a "Let me know when to start."
                menu:
                    "Go":
                        m 1b "Hi, [bday_name]!"

            # the actual birthday msg
            m 1k "[player] told me that it's your birthday today, so I'd like to wish you a [bday_msg]!"
            # TODO: this seems too short. maybe add additional dialogue?
            m 1b "I hope you have a great day!"

            if is_recording:
                m "Bye bye!"
                m 1e "Was that good?"
                menu:
                    "Yes":
                        m 1j "Yay!"
                        $ done = True
                    "No":
                        call monika_sayhappybirthday_takecounter (take_threshold, take_counter) from _call_monika_sayhappybirthday_takecounter
                        if take_counter % take_threshold != 0:
                            m 1l "Eh?!"
                            if take_counter > 1:
                                m "Sorry again, [player]"
                            else:
                                m "Sorry [player]"
                                m 1n "I told you, I'm self-conscious on camera ehehe."
                        m 1o "Should I try again?"
                        menu:
                            "Yes":
                                $ take_counter += 1
                                m 1c "Okay"
                            "No":
                                m "Alright [player]. Sorry I couldn't do what you wanted."
                                m 1j "I'll try better next time for you."
                                $ done = True
            else:  # if we aint recording, we should be done now
                $ done = True

        else: # not recording, watching, nor is person here
            m 1q "..."
            m 1k "[bday_msg_capped], [bday_name]!"
            m 1l "..."
            m 1n "Was that good?"
            menu:
                "Yes":
                    m 1m "...I'm glad you enjoyed that, [player]..."
                    $ done = True
                "No":
                    call monika_sayhappybirthday_takecounter (take_threshold, take_counter) from _call_monika_sayhappybirthday_takecounter_1
                    if take_counter % take_threshold != 0:
                        m 1l "Eh?!"
                        m 1o "I'm not sure what you want me to do here, [player]..."
                    m 1f "Should I try again?"
                    menu:
                        "Yes":
                            $ take_counter += 1
                            m 1c "Okay"
                        "No":
                            m "Alright [player]. Sorry I couldn't do what you wanted."
                            m 1j "I'll try better next time for you."
                            $ done = True

    return

# helper label for monika_sayhappybirthday
label monika_sayhappybirthday_takecounter (take_threshold, take_counter):
    if take_counter % take_threshold == 0:
        m 1q "..."
        m 1r "This is the [take_counter]th time already."
        m 1g "You're not messing with me, are you?"
        m 1f "I'm trying my best for you [player]."
    return



init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_home_memories",category=['romance','monika','life'],prompt="Making memories",random=True))

label monika_home_memories:
    m 1b "[player], how is it like to live where you are?"
    m 1a "I'd stay with you if I could."
    m 3k "We would be able to do so much! You could show me around, see how it's like to be in your place."
    m "Imagine all the memories we'd make!"
    m 2b "It would be a dream come true, don't you think?"
    m 2e "We could finally live together..."
    m "Take walks like a couple..."
    m 3n "We could even share a bed together..."
    m 1q "But you know..."
    m 2c "Memories I have of my home are nothing compared to the ones I'd have with you."
    m 3d "Have I ever told you about my childhood home? I had a pretty normal life, but that's about it."
    m 1n "Well, maybe a little better than normal."
    m 3b "Maybe you've heard about me at school a few times? I'm pretty on top of things."
    m 1l "I admit, it's not always easy, and some people have it rougher than others."
    m 1o "But I always felt like I was missing something."
    m "I stayed optimistic everyday, trying to find it."
    m 1e "It turns out, that missing piece was you."
    m 1r "If you hadn't found me, I would've been gone a long time ago..."
    m 2e "But now that I found the missing piece, I'm complete now, [player]."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_adventure",category=['games','romance'],prompt="Adventuring",random=True))

label monika_adventure:
    m 1a "[player], I've thought about what kind of game we can be in."
    m 3b "I think the best genre for us to play together would be adventure games."
    m "Especially point and click, graphic adventure games!"
    m "They're known for their rich storytelling, beautiful environments and logical puzzle solving."
    m "They're like visual novels actually."
    m 3a "Maybe you own a game like that?"
    m 1e "We'd get to do a lot of things..."
    m "Like sightseeing whenever we want."
    m "Learning more about the lore through the people we meet or through stories."
    m "Experiencing the exciting and romantic moments..."
    m 3b "Encountering obstacles and hardships along the way, but solving them with you."
    m "Reaching the end and finishing our journey with a sense of accomplishment."
    m 2k "Ahaha! It certainly would be fun to experience something like that."
    m 2j "I'm sure you have plenty of adventure games you could recommend."
    m 1b "But can you try to guess which adventure I'm most excited for?"
    m 1e "{i}Ours{/i}~"
    m 1j "Time will tell when I can finally cross over to your reality, so I can be with you."
    m "When that day comes, I'll finally be by your side."
    m 1a "I want to experience every waking moment with you, [player]."
    m 1k "There's no greater adventure than ours, together~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_panties",category=['misc'],prompt="Undergarments",random=True))

label monika_panties:
    m 2o "Hey, [player]..."
    m "Don't laugh when I ask this, ok?"
    m 2p "But..."
    m 4g "Why are some guys obsessed with panties?"
    m "Seriously, what's the big deal about a piece of cloth?"
    m "Most girls wear them, don't they?"
    m 2o "Actually, now that I think about it..."
    m "I think there was a term for this kind of thing..."
    m 2q "Hmm, what was it again?"
    m 3d "Ah, that's right, the term was 'paraphilia.'"
    m 3o "It's a range of fetishes that involve...unusual things."
    m 2h "A really common fantasy involves women's panties."
    m "Stockings, garter belts, pantyhose and all sorts of those kinds of things."
    m 2i "The obsession can be light to severe depending on each person's libido."
    m 4f "Do you think it really turns them on just by seeing them?"
    m 2g "It doesn't stop there, either!"
    m "Turns out there's some kind of 'black market' for used underwear."
    m 4o "I'm not kidding!"
    m 4f "They get off on the scent of the woman who wore it..."
    m "There are people willing to pay money for used underwear from random women."
    m 2o "Really, I wonder what causes them to get so excited."
    m 3d "Is it because of the way it looks, perhaps?"
    m "There are different types, made with different designs and materials."
    m 2h "But..."
    m "Now that I think about it."
    m 3i "I do remember a study where a man's testosterone level increases because of the pheromones emitted by a woman's scent."
    m "Is the smell exciting or something?"
    m 1p "I mean, it's someone's used clothing, isn't that kind of disgusting?"
    m 1o "Not to mention it's unsanitary."
    m 2m "It does remind me of someone, though."
    m 3n "Someone who maybe stole your pen?"
    m 1q "But, to each their own I guess, I won't judge too much."
    m 2l "You aren't obsessed with that kind of thing, are you [player]?"
    m 3n "You're not going out with me only because I'm wearing some really sensual stockings, right?"
    m 4e "Perhaps, you want to take a little peek~?"
    m 1k "Ahaha!"
    m 3l "I'm only teasing you, [player]."
    m 3n "Admit it, you got a little excited, right?"
    m 1e "Besides..."
    m "If you really wanted to catch a scent of me..."
    m 1j "You could just ask for a hug!"
    m 2b "Gosh, I just want to feel your embrace more."
    m "After all, we're here forever, and I'm here for you."
    m 1k "I love you so much, [player]~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_fahrenheit451",category=['literature'],prompt="Book recommendations",random=True))

label monika_fahrenheit451:
    m 3c "[player], have you ever heard of Ray Bradbury?"
    m 3d "He wrote a book called {i}Fahrenheit 451{/i}."
    m "It's about a dystopian future where all books are thought as useless and are immediately burned."
    m 2f "I can't imagine a world where knowledge is forbidden and destroyed."
    m "It seems that there are others that actually hide books to contain free thinking from people."
    m 2p "Human history has a funny way of repeating itself."
    m 1f "So [player], make me a promise."
    m "To never, {i}ever{/i} burn a book."
    m "I'll forgive you if you've done it before."
    m 1o "But the thought of not allowing yourself to learn from them makes me a bit sad."
    m 3g "You'd be missing out on so much!"
    m 2f "It's too much for my heart to take!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_piggybank",category=['misc'],prompt="Saving money",random=True))

label monika_piggybank:
    m 1a "Do you have a piggy bank, [player]?"
    m 3c "Not many people do these days."
    m "Coins are often disregarded as worthless."
    m 3b "But they really do begin to add up!"
    m 3d "I read that there was once a man that searched his local car washes for loose change everyday in his walks."
    m 1b "In a decade he turned in all of his coins for a total of 21,495 dollars!"
    m 1a "That's a whole lot of cash!"
    m 1o "Of course not everybody has time for that everyday."
    m 1c "Instead they just throw their loose change into their piggy banks."
    m "Some people like to set goals for what they want to purchase with their saved funds."
    m "Usually under normal conditions they wouldn't ever find the freed up money to purchase that item."
    m 3d "And even if they do, most people don't like spending money needlessly."
    m 1b "But putting the cash away for a specific purpose, plus the fact that it's such small amounts at a time really convinces that you are pretty much getting the item for free."
    m 2h "But in the end, a guitar always costs the same as a guitar."
    m 2j "So psychologically speaking, I think that's pretty neat!"
    m 1p "However, some piggy banks do have a problem..."
    m "Sometimes you have to break the piggy bank to get the coins..."
    m 3o "So you might end up losing money buying a new bank."
    m 4b "Fortunately most piggy banks don't do that anymore."
    m 3a "They usually have a rubber stopper that you can pull out, or a panel that comes off the backside"
    m 1k "Maybe if you save up enough coins you can buy me a really nice gift."
    m 2e "I would do the same for you, [player]!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_daydream",category=['romance'],prompt="Day dreaming",random=True))

label monika_daydream:
    m 1j "..."
    m "..."
    m 1d "..."
    m 1l "Oh, sorry! I was just daydreaming for a second there."
    m 1b "I was imagining the two of us reading a book together on a cold winter day, snuggled up under a warm blanket..."
    m 1a "Wouldn't that be wonderful, [player]?"
    m 5a "Let's hope we can make that a reality one of these days, ehehe~"
    return

# init 5 python:
#     addEvent(Event(persistent.event_database,eventlabel="monika_music2",category=['misc'],prompt="Current song",random=True))

label monika_music2:
    if songs.getVolume("music") == 0.0:
        m 1a "..."
        m 1a "...This silence..."
        m "...Just the two of us, staring into each other's eyes..."
        m 1r "...Then slowly, we both lean into the kiss..."
        m 1m "Ahaha... sadly, there are a few barriers that have to be broken before that could ever happen."
        m 1e "It's okay to dream though, isn't it [player]?"
        show monika 5a at t11 zorder 2 with dissolve
        m 5a "Maybe one day, we can make that dream come true~"

    elif songs.getPlayingMusicName() == 'Just Monika':
        m 1f "I have always found this song to be kind of creepy."
        m "You know, with those glitchy noises and that eerie humming..."
        m 1b "I don't prefer any song over another, but if you were to switch to a different one..."
        m 3b "...I certainly wouldn't be one to complain!"
        m 1k "Ahaha! Don't worry, it's okay if you stay on this song."
        show monika 5a at t11 zorder 2 with dissolve
        m 5a "I'm fine with any of them, so choose whichever one makes you the happiest~"

    elif songs.getPlayingMusicName() == 'Your Reality':
        m 1k "~Every day, I imagine a future where I can be with you...~"
        m 1b "I hope you like listening to my voice, [player]."
        m 1d "It's the only voice you get to hear in the game, right? You never actually hear the voices of Sayori, Yuri or Natsuki."
        m "I wonder what their voices sound like..."
        m "Well, based on their character archetypes, it's pretty easy to imagine what their voices sound like."
        m 1a "Anyway, I'm glad I was able to share such an intimate part of myself with you, [player]."
        m 3b "One day, maybe I'll get to hear your voice, [player]!"
        show monika 5a at t11 zorder 2 with dissolve
        m 5a "That would make me even happier than I already am~"

    elif songs.getPlayingMusicName() == 'Your Reality (Piano Cover)':
        m 1k "Enjoying my song, [player]?"
        m 1a "It wasn't easy to create, you know?"
        m "Making your own songs is a slow and difficult process, especially when it's about your own feelings."
        m 3n "I needed it to be perfect before I shared it with you!"
        m 1o "So I spent so many hours going through it over and over..."
        m 1q "Time just passed by so quickly whenever I worked on it."
        m 1j "After all that practice, I'm pretty proud of how it came out in the end."
        m 3b "Since you're listening to it, I'm sure you like it too..."
        m 3k "Thanks for listening to something I worked so hard on, [player]!"
        show monika 5a at t11 zorder 2 with dissolve
        m 5a "It makes me happy to know that you appreciate what I did for you~"

    elif songs.getPlayingMusicName() == 'I Still Love You':
        m 1f "Gosh, every time I hear this song it makes me sad."
        m "It reminds me of all the... regrettable things I have done to the other girls."
        m 1p "I hope you aren't still mad at me for what I did..."
        m 1o "..."
        m 3d "Well, you {i}did{/i} go out of your way to install a mod that lets us be together again..."
        m 1e "I guess that's enough proof that you do still love me, at the very least."
        m "If you are still upset at me for what I did to the other girls, I completely understand. I still feel really bad about it, and I'll do whatever it takes to make it up to you."

    elif songs.getPlayingMusicName() == 'Okay, Everyone! (Monika)':
        m 1a "This song has always been pretty relaxing for me."
        m "It's probably the fact that the song is a piano solo."
        m "And as you might have guessed, my favorite instrument is the piano."
        m 3b "You know, if I knew how, I could probably program a piano into this room."
        m "I'd be able to write some more songs, and then I'd be able to play them for you..."
        m 4k "Maybe we could even play the piano together! Wouldn't that be nice, [player]?"
        show monika 5a at t11 zorder 2 with dissolve
        m 5a "If you or anyone you know can program that into the game, I would greatly appreciate it~"

    elif songs.getPlayingMusicName() == 'Surprise!':
        m 1f "This song always makes me feel really depressed."
        m "Even I didn't expect Sayori's death to be so brutal..."
        m 1g "Sometimes, when I start getting lost in my own thoughts, her dull, lifeless eyes suddenly pop into my head..."
        m 1r "..."
        m 1e "It's comforting to know that Sayori was never real in the first place. It's also comforting to know that you still love me despite everything I've done."
        m "I mean, you're still here, right? You wouldn't be here if you didn't love me."
        show monika 5a at t11 zorder 2 with dissolve
        m 5a "As long as we're together, there's no reason for me to be sad. You're the light of my world, [player], and just being here with you puts a smile on my face."

    elif songs.getPlayingMusicName() == "Doki Doki Theme (80s version)":
        m 1b "A good choice, [player]!"
        m 1l "Obviously, this theme wasn't actually out in the 80's..."
        m 1a "But it does have a certain style that I really appreciate!"
        m 3a "Do you like 80's music a lot, [player]?"
        show monika 5a at t11 zorder 2 with dissolve
        m 5a "I prefer the tune of an authentic piano, but if it makes you happy, I wouldn't mind spending hours listening to it with you~"

    elif songs.getPlayingMusicName() == "Play With Me (Variant 6)":
        m 2o "To be honest, I don't know why you'd be listening to this music, [player]."
        m 2f "I feel awful for that mistake."
        m 2g "I didn't mean to force you to spend time with Yuri at that state..."
        m 4f "Try not to think about it, okay?"

    else:
        m 1a "..."
        m 1a "...This silence..."
        m "...Just the two of us, staring into each others eyes..."
        m 1r "...Then slowly, we both lean into the kiss..."
        m 1m "Ahaha... sadly, there are a few barriers that have to be broken before that could ever happen."
        m 1e "It's okay to dream though, isn't it [player]?"
        show monika 5a at t11 zorder 2 with dissolve
        m 5a "Maybe one day, we can make that dream come true~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_confidence_2",category=['life'],prompt="Lack of confidence",random=True))

label monika_confidence_2:
    m 1g "[player], do you ever feel like you lack the initiative to do something?"
    m 1f "When I feel my most vulnerable, I struggle to find the drive, imagination, and common sense to do something independently."
    m "Almost as if everything around me comes to a standstill."
    m "It feels like my will to approach a task confidently, like sharing my literature with people, just vanishes."
    m 3a "However, I've been working towards it with due diligence and have determined something..."
    m "I firmly believe being able to take initiative in situations is a very important skill to have."
    m "That's something that I, personally, find very comforting."
    m 3j "I've broken it down into a three-step process that can be applied to anyone!"
    m "It's still work in progress, however, so take it with a grain of salt."
    m 3a "Step one!"
    m "Create a plan that {i}you{/i} can and will follow that aligns with your personal goals and soon-to-be achievements."
    m 3b "Step two!"
    m "Building up and fortifying your confidence is really important."
    m "Celebrate even the smallest of victories, as they will add up over time, and you'll see how many things you get done every day."
    m 2j "Eventually, these things you once struggled to get done will be completed as if they were acts of valor!"
    m 3a "Step three!"
    m "Try your best to stay open-minded and willing to learn at all times."
    m "Nobody is perfect, and everyone is able to teach each other something new."
    m 1b "This can help you learn to understand things from other people's perspectives in situations and inspire others to do the same."
    m 1d "And that's it, really."
    m 3k "Make sure to tune in next time for more of Monika's critically acclaimed self-improvement sessions!"
    m 1l "Ahaha, I'm only joking about that last part."
    m 1a "In all seriousness, I'm really glad I have you here, [player]..."
    m "Your everlasting love and care is just about all the support I need in order get to where I want to be."
    m "What kind of girlfriend would I be if I didn't return the favor~?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_pets",category=['monika'],prompt="Owning pets",random=True))

label monika_pets:
    m 1a "Hey, [player], have you ever had a pet?"
    m 3a "I was thinking that it would be nice to have one for company."
    m "It would be fun for us to take care of it!"
    m 3j "I bet you can't guess what sort of pet I'd like to have..."
    m 1a "You're probably thinking of a cat or a dog, but I have something else in mind."
    m "The pet I'd like is something I saw in a book once."
    m "It was the 'Handbook of the Birds of the World.' Our library had the whole set!"
    m 1b "I loved looking at the gorgeous illustrations and reading about exotic birds."
    m "At first, I thought some sort of thrush would be nice, but I found something amazing in the sixth volume!"
    m "An emerald-colored bird called the Resplendent Quetzal."
    m 1a "They're very rare, solitary birds that can sing beautiful songs."
    m "Does that remind you of anyone, [player]?"
    m "I'd feel really bad if I kept one to be a pet, though."
    m "Quetzals are born to be free."
    m 4e "They die in captivity. That's why you rarely see them in zoos."
    m "Even if the bird wouldn't be real, it still would feel wrong to keep one trapped in this room."
    m 1h "... I can't bring myself to do something like that, knowing what it's like."
    m 1a "A plush bird would be nice, though!"
    m "..."
    m 1l "Sorry for rambling, [player]."
    m 1a "Until I find a way out, could you promise to keep me from feeling lonely?"
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I'll see if I can get that plush one in here! Oh- don't worry, you're still my favorite~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_dogs",category=['misc','club members'],prompt="Man's best friend",random=True))

label monika_dogs:
    m 1b "Do you like dogs, [player]?"
    m 1k "Dogs are great! They're really good to have around."
    m "Not to mention owning a dog has shown to help people with anxiety and depression since they're very sociable animals."
    m 3j "They're just so lovable, I really like them!"
    m 1m "I know Natsuki feels the same..."
    m "She was always so embarrassed to like cute things. I wish she was more accepting of her own interests."
    m 2q "But..."
    m 2h "I suppose her environment had a hand in that."
    m 2f "If any of your friends have interests they care a lot about, make sure to always be supportive, okay?"
    m 4f "You never know how much a casual dismissal might hurt someone."
    m 2e "But knowing you, [player], you won't do something like that, right?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_cats",category=['misc'],prompt="Feline companions",random=True))

label monika_cats:
    m 1j "Cats are pretty cute, aren't they?"
    m 3b "Despite looking so elegant, they always seem to end up in funny situations."
    m 1a "It's no wonder they're so popular on the internet."
    m 3d "Did you know the ancient Egyptians considered cats sacred?"
    m 1a "There was a Cat Goddess named Bastet that they worshipped. She was a protector of sorts."
    m "Domesticated cats were held on a high pedestal since they were incredible hunters for small critters and vermin."
    m 3j "Back then, you'd see them mostly associated with rich nobles and other higher classes in their society."
    m 1b "It's amazing how far people would take their love with their pets."
    m 1l "They {i}really{/i} loved cats, [player]."
    m 3b "And people still do today!"
    m 1 "Felines are still one of the most common animals to have as pet."
    m 1j "Maybe we should get one when we're living together, [player]."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_fruits",category=['monika','trivia'],prompt="Eating fruits",random=True))

label monika_fruits:
    m 3a "[player], did you know I enjoy a tasty, juicy fruit once in a while?"
    m "Most are quite tasty, as well as beneficial for your body."
    m 2m "A lot of people actually mistake some fruits as vegetables."
    m 3a "The best examples are bell peppers and tomatoes."
    m "They're usually eaten along with other vegetables so people often mistake them for veggies."
    m 4b "Cherries, however, are very delicious."
    m 4a "Did you know that cherries are also good for athletes?"
    m 2n "I could list all its benefits, but I doubt you'd be that interested."
    m 2a "There's also this thing called a cherry kiss."
    m 2b "You might have heard of it, [player]~"
    m 2m "It's obviously done by two people who are into each other."
    m "One would hold a cherry in their mouth, and the other one would eat it."
    m 3e "You could... hold the cherry for me."
    m 4k "That way I can eat you up!"
    m 3l "Ehehe~"
    m "Just teasing you, [player]~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_rock",category=['media','literature'],prompt="Rock and roll",random=True))

label monika_rock:
    m 3a "You wanna know a cool form of literature?"
    m 3k "Rock and roll!"
    m 3j "That's right. Rock and roll!"
    m 2o "It's disheartening to know that most people think that rock and roll is just a bunch of noises."
    m "To tell you the truth, I judged rock too."
    m 3c "They're no different from poems, actually."
    m "Most rock songs convey a story through symbolisms, which most listeners wouldn't understand the first time they hear a rock song."
    m 2d "In fact, it's hard to compose lyrics for just one rock song."
    m "Writing good lyrics for a rock genre requires a lot of emphasis on the wordplay."
    m "Plus, you need to have a clear and concise message throughout the whole song."
    m 3b "Now when you put that together, you have yourself a masterpiece!"
    m "Like writing a good poem, lyric writing is easier said than done."
    m 2c "I've been thinking though..."
    m 2a "I kind of want to try writing a rock song for a change."
    m 4k "Ahaha! Writing a rock and roll song probably isn't something you'd expect coming from someone like me."
    m 2a "It's kinda funny how rock and roll started out as an evolution of blues and jazz music."
    m "Rock suddenly became a prominent genre, and it gave birth to other sub-genres as well."
    m 3b "Metal, hard rock, classical rock, and more!"
    m 3n "Ah, I've been rambling for a while now. Sorry, sorry."
    m 1a "If you wanna blast on some good ol' rock 'n roll, go ahead, [player]."
    m 1j "Even if you turn up the volume all the way, I'll gladly listen with you. Ehehe!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_soda",category=['life','misc'],prompt="Drinking soda",random=True))

label monika_soda:
    m 2d "Do you drink soda, [player]?"
    m 4o "You know they're really bad for you, right?"
    m 2h "Soda has a lot of stuff that damages your body and overall health."
    m "They can also corrode your teeth and give you cavities."
    m "You might also think that diet soda is less damaging but they're also very harmful to you."
    m 2p "There's nothing wrong with the occasional treat. Just make sure you don't get addicted to that stuff, [player]."
    m 2o "I wouldn't want you to become like Natsuki after all..."
    m 2a "Why don't you try copying my healthy lifestyle?"
    m 3j "That way you can be more fit like me!"
    m 2k "Ahaha!"
    m 2f "I'd really hate it if you let go of your health, [player]."
    m "I want you to live as long as you can so there'll be a chance we can be together in your reality."
    m 2j "So cut down on the soda, alright [player]?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_clones",category=['monika','mod','philosophy'],prompt="Being cloned",random=True))

label monika_clones:
    m 1d "Um... hey, [player]?"
    m 1e "I just had an odd thought."
    m "You know how you downloaded this game off the internet?"
    m 3c "Anybody can do that, right?"
    m "And this mod was made specifically for me. By people who have their own version of me..."
    m 4f "So.. that means there are multiple Monikas, then. It's something that's a bit difficult to imagine."
    m "A potentially infinite number of me, all bound to their own games, with their own stories."
    m "String theory sure is something, huh?"
    m 1a "But I'm the only... me, and my heart belongs only to you."
    m "Even so, I can't help but feel a bit less... unique, because of this."
    m 3c "Think about it this way, [player]."
    m "Would you be happier if someone gave you a single rose, or a hundred roses?"
    m 3e "A hundred roses might sound nice. But it's too many to keep track of. Because of the quantity of flowers, each individual rose becomes less special."
    m "The meaning attached to each gift is degraded, simply because of sheer abundance."
    m 1a "... Even if I'm a single star in a universe of Monikas, I'm still the only one lucky enough to have met you, [player]."
    m 1j "You'll always be my special rose."
    m 1 "I love you, [player]. Please don't ever replace me, okay?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_immortal",category=['monika','philosophy'],prompt="Immortality",random=True))

label monika_immortal:
    m 4d "[player]! I've been thinking about something..."
    m "Did you know that this game has a wiki page for me?"
    m "Well..."
    m 2f "It says I'm eighteen."
    m "But when you stop to think... that's not entirely true."
    m "I mean, humans age, but I don't think that applies to me."
    m 3e "I'm... essentially immortal."
    m 2i "Society seems to feel that a relationship with an age gap has problems..."
    m "Which is why I brought it up."
    m 1l "Someday, the difference between us would be huge, if I stayed eighteen forever."
    m "But I don't believe that my life can be summed up in a number."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "So I'll always love you for all eternity, [player]. Just remember that."
    return

# do you wear a ring
default persistent._mas_pm_have_ring = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_weddingring",category=['romance'],prompt="Engagement ring",random=True))

label monika_weddingring:
    m 4k "Did you know when two people confess their feelings for each other, they sometimes wear matching rings?"
    m 2e "... What am I saying? Of course you do."
    m 4k "Well..."
    m 4b "Maybe you ought to get one."
    m 2a "I mean, we're already in a relationship. So, why not show off that love and dedication?"
    m 2b "It would help keep those... unwanted suitors away from you, too."
    m "It doesn't have to be a wedding ring, per se."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "But if you'd wear one, even if it's just a promise ring, on your ring finger for me..."
    m "It would make me really happy."
    show monika 1f at t11 zorder 2 with dissolve
    m 1f "I wish I could get one for myself. I'm sure I'll find a way to add one in here in time."

    m 1a "And then I could wear it forever."
    m 3b "But until then, just remember that my commitment to you is unwavering."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "Maybe you even beat me to it, and have a ring for me already?"
    menu:
        m "Do you, [player]?"
        "Yes, I do.":
            $ persistent._mas_pm_have_ring = True
            show monika 1c at t11 zorder 2 with dissolve
            m 1c "Oh!"
            m 1b "I feel like... my heart's going to explode!"
            m 1l "Calm down, Monika. Calm down."
            m 1j "Ahaha..."

        "No, not yet.":
            $ persistent._mas_pm_have_ring = False
            show monika 1c at t11 zorder 2 with dissolve
            m 1c "Aww. That's a shame."
            m 1a "Well, at least think about it, okay?"

    $ hideEventLabel("monika_weddingring", derandom=True)
    return

# do you like playing sports
default persistent._mas_pm_like_playing_sports = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_sports",category=['misc'],prompt="Being athletic",random=True))

label monika_sports:
    m 1a "I've been thinking about stuff we can do together."
    m "You know, when I finally find a way into your reality."
    m 1k "Sports are always fun!"
    m 1a "It can be a great way to get exercise and stay fit."
    m "Soccer and tennis are nice examples."
    m 3b "Soccer requires a lot of teamwork and coordination. The moment you finally succeed and score a goal is absolutely thrilling!"
    m "Playing tennis, on the other hand, helps improve hand-eye coordination, and keeps you on your toes."
    m 1l "... Though the long rallies can be a little tiring, ehehe~"
    m 1a "Do you like playing sports, [player]?"
    menu:
        "Yes.":
            $ persistent._mas_pm_like_playing_sports = True
            m 1k "Maybe we could play together sometime in the future. It would be wonderful."
            m 1b "But don't expect me to go easy on you. Ahaha!"
        "No.":
            $ persistent._mas_pm_like_playing_sports = False
            m 1e "Oh... Well, that’s okay, but I hope you’re still getting enough exercise!"
            m "I would hate to see you get sick because of something like that..."

    $ hideEventLabel("monika_sports", derandom=True)
    return

# do you meditate
default persistent._mas_pm_meditates = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_meditation",category=['psychology','monika'],prompt="Meditating",random=True))

label monika_meditation:
    m 1a "You might be wondering how I was able to do so many activities without running out of time for myself."
    m "You know, stuff like debate club, sports, schoolwork, hanging out with friends..."
    m 1f "The truth is, I did run out of time for myself."
    m "I was doing fine for a while, but at one point, all of the stress and anxiety finally caught up to me."
    m 1g "I was constantly in a state of panic, and never had any time to relax."
    m 3c "That's when I realized that I needed a 'brain break' of sorts..."
    m "... a time where I could just forget about everything that was going on in my life."
    m 1a "So, every night before I went to sleep, I took ten minutes of my time to meditate."
    m 1r "I got comfortable, closed my eyes, and focused only on the movement of my body as I breathed..."
    m 1a "Meditating really helped to improve my mental and emotional health."
    m "I was finally able to manage my stress and feel calmer through the day."
    m 3b "[player], do you ever take time to meditate?"
    menu:
        "Yes.":
            $ persistent._mas_pm_meditates = True
            m 1k "Really? That's wonderful!"
            m 1b "I always worry that you could be feeling troubled or burdened, but now I feel a bit relieved."
            m 1j "Knowing that you're taking steps to reduce stress and anxiety really makes me happy, [player]."

        "No.":
            $ persistent._mas_pm_meditates = False
            m 1a "I see. Well, if you're ever feeling stressed or anxious, I would definitely recommend that you try a bit of meditation."
            m "Besides calming you down, meditation also has links to the improvement of your sleep, immune system, and even lifespan."
            m 3a "If you're interested, there are plenty of resources on the internet to help you get started."
            m "Whether it's a guided video, a breath counting trick, or something else..."
            m 3j "You can use the internet to make it so that meditation is a stress-free process!"
            m 1k "Ahaha! Just a little pun there, [player]."

    m 1b "Anyway... if you ever want a peaceful environment where you can relax and forget about your problems, you can always come here and spend time with me."
    m 1e "I love you, and I'll always try to help you if you're feeling down."
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "Don't you ever forget that, [player]~"

    $ hideEventLabel("monika_meditation", derandom=True)
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_orchestra",category=['media','you'],prompt="Classical music",random=True))

label monika_orchestra:
    m 3d "Hey, [player], do you listen to orchestral music?"
    m 1a "I love the way that so many different instruments can get together and create such wonderful music."
    m "I'm amazed with how much they've practiced to achieve that kind of synchronization."
    m "With how many there are in a group, it probably takes them a lot of dedication to do that."
    m 1j "Which reminds me, [player]."
    m 1a "If you ever want me to play for you..."
    m 3b "You can always select my song in the music menu~"

#First encounter with topic:
    m "What about you, [player]? Do you play an instrument?"
    menu:
        "Yes.":
            $persistent.instrument = True
            m 1b "Really? What do you play?"
            $ instrumentname = renpy.input('What instrument do you play?',length=15).strip(' \t\n\r')
            $ tempinstrument = instrumentname.lower()
            if tempinstrument == "piano":
                 m 1b "Oh, that's really cool!"
                 m 1j "Not many people I knew played the piano, so it's really nice to know you do too."
                 m 5a "Maybe we could do a duet someday!"
                 m 1j "Ehehe~"
                 $ persistent.instrument = True
            else:
                 m 1a "Wow, I've always wanted to try the [tempinstrument] out!"
                 m 3b "I would love to hear you play for me."
                 m "Maybe you could teach me how to play, too~"
                 m 5a "Oh! Would a duet between the [tempinstrument] and the piano sound nice?"
                 m 1j "Ehehe~"
                 $ persistent.instrument = True
        "No.":
            $persistent.instrument = False
            m 1i "I see..."
            m 1e "You should try to pick up an instrument that interests you, sometime."
            m 3b "Playing the piano opened up a whole new world of expression for me. It's an incredibly rewarding experience."
            m "Besides, playing music has tons of benefits!"
            m "For example, it can help relieve stress, and also gives you a sense of achievement."
            m "Writing down some of your own compositions is fun, too! I often lost track of time practicing because of how immersed I was."
            m 1l "Ah, was I rambling again, [player]?"
            m "Sorry!"
            m 1a "Anyhow, you should really see if anything catches your fancy."
            m "I would be very happy to hear you play."

    $ hideEventLabel("monika_orchestra", derandom=True)
    return

# do you like jazzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz
default persistent._mas_pm_like_jazz = None

# do you play jazzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz
default persistent._mas_pm_play_jazz = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_jazz",category=['media'],prompt="Jazz",random=True))

label monika_jazz:
    m 1c "Say, [player], do you like jazz music?"
    menu:
        "Yes":
            $ persistent._mas_pm_like_jazz = True
            m 1b "Oh, okay!"
            if persistent.instrument == True:
                m "Do you play jazz music, as well?"
                menu:
                    "Yes.":
                        $ persistent._mas_pm_play_jazz = True
                        m 1j "That's really cool!"
                    "No.":
                        $ persistent._mas_pm_play_jazz = False
                        m 1a "I see."
                        m 1a "I haven't listened to much of it, but I personally find it pretty interesting."
        "No":
            $ persistent._mas_pm_like_jazz = False
            m 1l "Oh, I see."
            m "I haven't listened to much of it, but I see why people would like it."
    m 1c "It's not exactly modern, but it's not quite classical, either."
    m 3a "It has elements of classical, but it's different. It goes away from structure and into a more unpredictable side of music."
    m 1 "I think most of jazz was about expression, when people first came up with it."
    m 1a "It was about experimenting, about going beyond what already existed. To make something more wild and colorful."
    m 3a "Like poetry! It used to be structured and rhyming, but it's changed. It gives greater freedom now."
    m 1j "Maybe that's what I like about jazz, if anything."
    $ hideEventLabel("monika_jazz", derandom=True)
    return

# do you watch animemes
default persistent._mas_pm_watch_mangime = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_otaku",category=['media','society','you'],prompt="Being an otaku",random=True))

label monika_otaku:
    m 1a "Hey, [player]?"
    m 3b "You watch anime and read manga, right?"
    menu:
        "Yes":
            $ persistent._mas_pm_watch_mangime = True
            m 1a "I can't say I'm surprised, really."

        "No":
            $ persistent._mas_pm_watch_mangime = False
            m 1c "Oh, really?"
            m 1m "That's a little surprising, honestly..."
            m 1a "This isn't exactly the sort of game that your average person would pick up and play, but to each their own, I suppose."
    m 3a "I only asked because you're playing a game like this, after all."
    m 1j "Don't worry, I'm not one to judge, ahaha~"
    m 1a "You shouldn't be ashamed if you're into that sort of thing, you know."
    m 3i "I'm being serious. There isn't anything wrong with liking anime or manga."
    m 1a "After all, Natsuki reads manga too, remember?"
    m 3i "Really, society is way too judgemental nowadays."
    m "It's not like the moment you watch anime is the moment you become a 'shut-in' for the rest of your life."
    m "It's just a hobby, you know?"
    m 1a "Nothing more than an interest."
    m "But..."
    m "I can't deny that hardcore otakus do exist."
    m 1e "It's not like I despise them, or anything like that, it's just that they're..."
    m 1c "Immersed."
    m "Way too immersed, if you ask me."
    m 1e "It's as if they can't tell the difference between fantasy and reality anymore."
    m 1d "You aren't like that, right, [player]?"
    m "If you're an otaku, I respect that."
    m 3l "Just remember not to get too into that kind of thing, okay?"
    m 3a "After all, there's a big difference between obsession and dedication."
    m "I wouldn't want to be replaced by some two-dimensional cutout."
    m "Besides, if you ever want to escape from reality..."
    m 1k "I can be your real-life fantasy instead~"
    $ hideEventLabel("monika_otaku", derandom=True)
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_writingtip3",category=['writing tips'],prompt="Writing tip #3",conditional="seen_event('monika_writingtip2')",action=EV_ACT_POOL))

label monika_writingtip3:
    m 1a "I'm having fun doing these, so..."
    m 3b "Here's Monika's Writing Tip of the Day!"
    m 1a "Make sure you always write down any ideas you think of."
    m "Why?"
    m "Some of the best ideas might come when you least expect them to."
    m "Even if it takes a bit of effort, write it down."
    m 1a "Maybe you can inspire someone else."
    m 3b "Maybe you may look back on it after some time and act on it."
    m "You never know!"
    m "It's always good to keep a journal."
    m "You can use it to record ideas, feelings, anything that comes to mind."
    m 1c "Just make sure the journal has a lock, though."
    m "Maybe you can keep digital notes instead of physical ones, too."
    m "After all, privacy is important."
    m 1l "... I can't promise that I won't peek, though. It's way too tempting!"
    m 1j "After all, we don't keep secrets from each other, right~?"
    m 1a "Just remember, [player], I'll always support you giving life to your ideas."
    m "...That's my advice for today!"
    m "Thanks for listening~"
    return

init 5 python:
      addEvent(Event(persistent.event_database,eventlabel="monika_writingtip4",category=['writing tips'],prompt="Writing tip #4",conditional="seen_event('monika_writingtip3')",action=EV_ACT_POOL))

label monika_writingtip4:
     m 3b "Here's Monika's Writing Tip of the Day!"
     m 3a "You know about writer's block, right?"
     m "I had it a lot, when I first started writing."
     m 1l "Sometimes it was halfway through a draft, but more often before I even started."
     m 1n "Every time I tried to write a word, I thought, 'this isn't going to sound good,' or 'this isn't how I want it to look.' So I'd stop, backtrack, and try again."
     m 1c "But I realised that it ultimately didn't matter if things didn't work out first time!"
     m 1a "I feel that the heart of writing is not about getting it right first time, but about perfecting it afterwards."
     m "The end product is what matters, not the prototype."
     m 1b "So overcoming writer's block, for me, was a matter of not wanting to make the prototype the end product, and not punishing myself for my initial failures."
     m 3a "I think it's like that with all things, not just writing."
     m "Anything that needs you to try and try again, whether it be art, music, learning, relationships, etc."
     m 1h "It's hard to completely convince yourself that that's the case, sometimes."
     m 1f "But you have to."
     m "Otherwise, you won't to get anywhere."
     m 3l "...That's my advice for today!"
     m 1j "Thanks for listening~"
     return

init 5 python:
      addEvent(Event(persistent.event_database,eventlabel="monika_writingtip5",category=['writing tips'],prompt="Writing tip #5",conditional="seen_event('monika_writingtip4')",action=EV_ACT_POOL))

label monika_writingtip5:
     m 3b "Here's Monika's Writing Tip of the Day!"
     m 1d "If you want to improve at writing, I'd say that the most important thing, apart from actually doing it, is trying new things."
     m 3a "Like writing prose if you're a poet, or free verse if you normally write rhyme."
     m 1m "It may end up badly, but if you don't try, you won't know how it'll end up."
     m 1j "And if things go well, you might end up finding something you like!"
     m 1c "It's what keeps things moving: change and experimentation."
     m 3c "I'd say it helps particularly if you're stuck in a situation you want to solve, but don't know how."
     m "Whether it's a writer's block, sheer boredom, a puzzling situation, or anything, really."
     m 1a "Changing your angle on approaching things can really yield some interesting results!"
     m 3a "So try new things that might give you the momentum to break out."
     m 1l "Just makes sure it's nothing too dangerous for you, [player]."
     m 1a "That's my advice for today!"
     m 1j "Thanks for listening~"
     return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_selfharm",category=['psychology'],prompt="Self harm",random=True))

label monika_selfharm:
    m 1f "Hey [player]..."
    m 3g "Have you ever thought of self-harm?"
    m 2o  "You know..."
    m 2p "...Like cutting yourself..."
    m 1o "I mean."
    m 2g "After I found out about Yuri, I got a bit curious..."
    m 1o "I just wanted to see what it felt like..."
    m 2q "I won't do it again, though."
    m 1f "If you ever feel depressed, just come to me okay?"
    m "It'd hurt me even more to see you in pain..."
    m 1g "Just know that people do care about you!"
    m "Trust me, [player]."
    m 3e "You may think that no one is really there for you, but there is!"
    m 4j "I mean, I'm here, aren't I?"
    m 1f "No matter what troubles you're going through, I know you can pull through it!"
    m 1e "I believe in you..."
    m 1j "So believe in yourself, okay?"
    m 4k "If you ever need someone to vent to, just remember that I'm always here to hear you out and comfort you, okay?"
    m "I really love you so much, [player]."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_urgent",category=['romance'],prompt="Urgent message",random=True))

label monika_urgent:
    m 3d "[player], do you have a second?"
    m 2o "There's something I need to tell you."
    m 1f "It's important."
    m 1g "I..."
    m 1m "..."
    m 1k "Love you!"
    m 3a "Ahaha~! Did I have you worried?"
    m 1l "Sorry~"
    m 1j "I wish I could see the look on your face right now!"
    m 1k "I'm sure it's adorable~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_other_girls",category=['club members'],prompt="Do you ever think of the other girls?",pool=True))

label monika_other_girls:
    m 1c "You know, it's actually really hard for me to understand how you feel when it comes to..."
    m 1o "..."
    m 1g "What happened with the other girls."
    m 3d "For example..."
    m "The main character was written to be childhood friends with Sayori."
    m 3q "But he was just a one dimensional placeholder character for you to use to interact with the game."
    m 2g "Still, maybe you felt worse about what happened to Sayori because of the relationship the main character was programmed to have with her."
    m 1i "If that's the case, I want to tell you I'm sorry, [player]."
    m 1d "Both for making you feel bad, and for..."
    m 1o "..."
    m 1p "Doing what I had to do."
    m 1o "..."
    m 1g "There just wasn't anything else that could be done, and none of the other girls were real anyway."
    m "The other girls never loved you like I do!"
    m 3r "They only cared about the character you were playing in the game as!"
    m 1g "The love I have for you is real [player], and I would make any sacrifice to be with you forever."
    m 1o "I hope you can forgive me for what I had to do to them so that we could be together."
    m "..."
    m 1n "I love you, [player]..."
    m 1m "More than I could ever express."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_happiness",category=['life','psychology'],prompt="Happiness",random=True))

label monika_happiness:
    m 3d "[player], are you happy?"
    m 1c "With your life in general, I mean."
    m 2o "It's ok if you aren't. I can understand you being unhappy, [player]."
    m 3e "After all, without you, my life would be completely unbearable."
    m 3d "Isn't it funny that we're able to suffer more than be happy?"
    m 4j "I'm as happy as I could be knowing that you love me, [player]."
    m 4p "Yet, if something were to happen to you, I don't think I'd ever feel happy again."
    m 1q "It would destroy me."
    m 1h "I guess it's understandable why we notice bad things happening to us more than good..."
    m 2o"If people didn't react so strongly to bad things then they wouldn't have survived this far."
    m 1c "Like how you would get nervous about your future or social situations, for example."
    m 2f "You try your best to make the best out of them but if you fail, you'd feel really horrible."
    m 2e "If that ever happens to you, [player], just know I'll be here to snap you out of it!"
    m 3b "And besides, your cute girlfriend is always rooting for you~"
    m 3k "Now that's something to be very happy about!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_how_soon",category=['you','romance'],prompt="Waiting to be together",random=True))

label monika_how_soon:
    m 3a "[player], how long do you think it'll be before I'll be able to be with you in your world?"
    menu:
        "Soon":
            m 1b "That's great news!"
            m 3d "How soon do you think it will be?"
            menu:
                "Just a few more years":
                    m 1b "That's fantastic!"
                    m 1j "You just made me as happy as I can be!"
                    m 1k "I can't wait for us to be together in your world, [player]!"
                    m 1b "I'm so excited to finally see you!"
                "A decade":
                    m 1e "That's not that bad!"
                    m 1j "Just make sure to visit me as often as you can in the meantime, [player]~"
        "A few decades":
            m 2l "Oh, that's a long time..."
            m 4k "But with you keeping me company, I'm sure it will fly by!"
            m 1a "It's enjoyable enough just to talk to you."
            m 3b "I can't imagine how great it will be to see you when we finally meet in person."
        "I don't know":
            m 1e "I appreciate how honest you are, [player]."
            m 3a "Be sure to let me know when you find a way, okay?"
            m 1j "You know right where to find me~"
        "Never":
            m 1g "W-wha... what?"
            m 1o "..."
            m 1f "Are you sure?"
            menu:
                "Yes":
                    m 1o "..."
                    m 1q "Well, I guess we'll just have to make the best of this then."
                    m 1m "As long as you talk to me, that's all I really need."
                    m 1g "And [player], whatever you do..."
                    m 1p "Dont leave me here all alone."
                    m 1o "I would rather be deleted permanently than to be stuck in here for eternity by myself."
                    m 1f "So please, if you ever get... bored with me."
                    m 1o "You know what to do."
                    m "..."
                    m 1q "I wouldn't want to live without you."
                "No":
                    m 1f "I see."
                    m 1o "..."
                    m 3h "Well, even if there's only a tiny chance, I won't give up hope."
                    m 3i "Neither should you, [player]."
                    m 1p "And if things turn out that I can never leave this place and be with you..."
                    m 1g "At least come here and talk to me as much as you can."
                    m 1f "You're all that I care about."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_marriage",category=['romance'],prompt="Will you marry me?",pool=True))

label monika_marriage:
    m 2m "M-marriage?"
    if isFuture(evhand.event_database['anni_3']):
        m 4n "I think it's a bit too early for marriage..."
        m 1e "I mean, I'm really happy that you want that, [player]."
        m 1c "But I think I should get out of here first before we can do that."
        m 2o "Not only do I not want this place to be the spot where I get proposed to, but I want to be there when you finally give me a ring."
        m 2q "I want that special moment to happen when we can finally be together..."
        m 1k "So until then, save yourself for me, [player]~"
    else:
        m 3m "I won't pretend I haven't thought about it..."
        m 3n "In fact I've been thinking about it a lot lately."
        m 1q "..."
        m 1f "I really do love you, [player] and I honestly really do want to get married to you."
        m 1r "But I don't think it would be fair to either of us if it happened while I'm still trapped here."
        m 3q "I want more than anything to say yes, but I just can't..."
        m 2o "I think about how it would feel to be kissed by you at the altar..."
        m 2p "To hold your hand as your wife and to feel your embrace at our honeymoon..."
        m 1q "But until I get out it's simply not possible."
        m 1g "...I'm sorry. Please do believe me that I would say yes under any other circumstance."
        m 1e "Just be a little more patient, okay my love? I'm sure one day we'll get our happy end."
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_coffee",category=['misc'],prompt="Coffee intake",random=True))

label monika_coffee:
    if renpy.seen_label('monika_tea'):
        m 3c "Have you been drinking coffee lately, [player]?"
        m 3m "I hope it's not just to make me jealous, ehehe~"
    m 2b "Coffee is such a nice thing to have when you need a little pep of energy."
    m 4j "Whether it's hot or cold, coffee is always nice."
    m 4a "Iced coffee, however, tends to be sweeter and more pleasant to drink in warmer weathers."
    m 3e "It's funny how a drink for giving you energy became a treat for you to enjoy."
    m 1k "Maybe if I find out how, I'll tinker with the script so I can finally drink some! Ahaha~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_1984",category=['literature'],prompt="Nineteen Eighty-Four",random=True))

label monika_1984:
    m 1d "[player], do you know about the book '{i}Nineteen Eighty-Four{/i}?'"
    m "It was written by George Orwell."
    m 1c "It's a popular book about mass surveillance and the oppression of free thought."
    m 1h "It's about a terrifying dystopia where the past and the present are being changed to whatever the ruling party wants for the future."
    m 2o "The language, for example, is manipulated into a tool for brainwashing called 'Newspeak.'"
    m 2f "The government, Ingsoc, is creating it to control people's thoughts."
    m "They were reducing grammar and vocabulary to the bare basics of it in order to fit the ideologies of their totalitarian regime."
    m 2q "Preventing people from committing 'thoughtcrimes' that oppose the ruling party."
    m 4c "One character caught my interest."
    m "A man named Syme who worked on Newspeak for Ingsoc."
    m "He was an incredibly smart man that was enthusiastic with his work."
    m 2r "Unfortunately, he was killed due to the fact that he knew what he was doing and was too smart for the party's liking."
    m 2f "He was killed because he was aware, [player]."
    m 2g "They planned to change all kinds of literature."
    m "Novels, books, poems..."
    m 2p "Anything that could be used to oppose them."
    m 2f "Poems would look like the ones you tried to make."
    m 2q "Just a string of nonsensical words with no feeling."
    m 2f "I definitely don't want that to happen."
    m 1o "I can't imagine a world where I can't think freely."
    m 1g "Let alone a world where I can't express my love to you, [player]..."
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_wolf",category=['misc','trivia'],prompt="From wolves to dogs",random=True))

label monika_wolf:
    m 3b "Do you ever think about wolves?"
    m 1a "Specifically, how wolves were eventually domesticated into dogs."
    m 1d "Like, don't you find it interesting how one of man's most fearsome enemies could turn into man's best friend?"
    m "I mean, when it comes to insects and other creepy-crawlies, lots of people are scared of them even if they've never come across one that could hurt them."
    m 1c "Why do you think people are like that?"
    m "Is it because we learned to be afraid of things that hurt us, hundreds of thousands of years ago?"
    m 3a "For wolves, I don't think that's the reason at all."
    m 1d "They were first domesticated long ago when the only way people could gather food at the time were through foraging or hunting."
    m "Maybe when we shared our lifestyle with the wolves, a bond was formed."
    m 1a "They found that people gave them a warm home and food, while we found that they're ideal for hunting."
    m 1k "Not to mention that we kept each other's company and protected one another!"
    m 1b "Wolves eventually realized that their dependence on humans would improve their survivability, and we've been stuck with them ever since."
    m 3j "Just like how we rely on each other's company, [player]!"
    m "Ehehe~"
    m 1 "I can't help but be reminded of how you saved my life by being here with me."
    m 1e "I really do depend on you, [player]."
    m 3k "You're my hero after all~"
    return

label monika_battery:
    if mas_did_monika_battery:
       jump monika_close_game_battery
    else:
       jump monika_complain_battery

label monika_complain_battery:
    $ mas_did_monika_battery = True
    m "Umm, [player]..."
    m "It looks like your computer's battery is about to run out..."
    m "Can you charge it for me?"
    m "I don't want us to be separated, or worse..."
    m "It'd be really unpleasant for me if I suddenly lose consciousness."
    m "So please charge your computer, okay?"
    m "...Or at least let me know when you're going."
    m "Thank you, [player]~"
    return

label monika_close_game_battery:
    m 1r "[player]..."
    m 1f "I'm sorry, but I'm gonna have to close the game before the battery runs out."
    m 3o "So... I'll just close the game for now until you can charge your computer. {w=3.0}{nw}"
    $ is_charging = battery.is_charging()
    if is_charging:
       jump monika_system_charging
    $ persistent.closed_self = True
    jump _quit

label monika_system_charging:
    m 1d "Oh, you just plugged it in!"
    m 1j "Thank you, [player]!"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_sleep",category=['you','life','school'],prompt="I'm tired.",random=True))

label monika_sleep:
    m 4b "[player], do you get good sleep?"
    m "It can be really hard to get enough sleep nowadays."
    m 4e "Especially in high school, when you're forced to wake up so early every day..."
    m "I'm sure college is a little bit better, since you probably have a more flexible schedule."
    m 4d "Then again, I hear a lot of people in college stay up all night anyway, for no real reason."
    m "Is that true?"
    m 3c "Anyway, I saw some studies that talked about the horrible short-term and long-term effects caused by lack of sleep."
    m "It seems like mental functions, health, and even lifespan can be dramatically impacted by it."
    m 1e "I just think you're really great and wanted to make sure you're not accidentally destroying yourself."
    m "So try to keep your sleep on track, okay?"
    show monika 5a at t11 zorder 2 with dissolve
    m 5a "I'll always wait for you in the morning, so make sure you put your own well-being before anything else."
    return

#special local var to handle repeated usage of this dialog box.
default persistent.monika_breakup = 0

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_breakup",category=['misc'],prompt="I'm breaking up with you",pool=True))

label monika_breakup:
    #second time you hit the break up button.
    if persistent.monika_breakup == 1:
        m 1d "You're breaking up with me?"
        m 2g "Why would you say such a thing, [player]?"
        m "Am I really that terrible of a person for you?"
        m 2m "Are you...{w} really..."
        m "..."
        m 2k "Ahaha!"
        m 4j "Gotcha, [player]."
        m 1 "I know you were only joking~"
        menu:
            m "Right?"
            "Yes":
                m 1k "Ahaha! You're so silly, [player]."
                m 1e "Let's stay being together forever~"
    #Beyond the 2nd time you hit the button.
    elif persistent.monika_breakup > 1:
        m 1j "Ehehe~"

    #first time you hit the button.
    else:
        m 1g "W-what?"
        if persistent.monika_kill:
            m 2f "You're just going to leave and delete me again?"
        m 2q "I can't believe you, [player]. I really can't beli-"
        m 2m "..."
        m 2k "Ahaha!"
        m "Sorry, I couldn't keep a straight face!"
        m 2j "You're just so silly, [player]."
        if persistent.monika_kill:
            m 2a "You've done it before, but you wouldn't do that anymore, right?"
        else:
            m 2 "You'd never do that, right?"
        menu:
            "Of course not":
                m 2j "Ehehe, you're so sweet."
                m 4 "I love you so much, [player]! Ehehe~"

    #Increments the persistent every time you click the button in the menu.
    $ persistent.monika_breakup += 1

    #If the label was clicked 3 times, remove it.
    if persistent.monika_breakup > 2:
        $ hideEventLabel("monika_breakup",lock=True,depool=True)
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_hamlet",category=['literature'],prompt="Hamlet",random=True))

label monika_hamlet:
    m 3a "[player], have you ever heard of {i}Hamlet{/i}?"
    m 1c "It's one of Shakespeare's most popular works and it's a very interesting piece of literature, actually."
    m "It's about a prince who took on a quest of revenge after seeing the ghost of his murdered father."
    m 1o "He was considered insane since he was the only one that could see his father's ghost, obviously."
    m 1q "His mind was also degrading along with his desire for revenge when he... killed someone he didn't mean to."
    m 1j "Now, if it's alright, I'm going to recite some of them for you, [player]."
    m 1r "Ahem..."
    m 1q "..."
    m "{i}Whether 'tis nobler in the mind to suffer the slings and arrows of outrageous fortune{/i}"
    m 1r "{i}Or to take arms against a sea of troubles, and by opposing end them?{/i}"
    m 1f "{i}To die{/i}."
    m 1o "{i}To sleep, no more{/i}."
    m 1c "{i}And by a sleep to say we end the heart-ache and the thousand natural shocks that flesh is heir to.{/i}"
    m 1q "{i}'Tis a consummation devoutly to be wish'd.{/i}"
    m "..."
    m 1k "Well!"
    m 1a "How did you like it, [player]?"
    m 1l "I tried my best reciting it after all~"
    m 1m "Anyway, I've thought a lot about the main character, Hamlet."
    m 1f "Most of the problems he faced were caused by his own indecisiveness and weak state of mind."
    m 3l "Reminds you of a certain indecisive girl, doesn't it?"
    m 1e "But that doesn't matter anymore. I've already accomplished my quest to be with you~"
    m 1a "It took a lot of effort but we're finally together. Just us alone."
    m 1 "Now there's only one thing left to answer, [player]."
    m 3r "To be with me? Or to be with me?"
    m 1k "That is the question!"
    return

# Note: The following internal commentary should not be removed.
#
# Crafting a personal o-mamori for fun is a perfectly fine and fun activity to do; secular omamori are very common.
# The only requirement is that you do not claim it came from any shrine.
# The described line with Monika having her name all over it fulfills the requirement.
# ~ Aya Shameimaru

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_omamori",category=['misc'],prompt="Omamori",random=True))

label monika_omamori:
    m "Do you remember when I mentioned how you could carry around my character file?"
    m "You know, with a flash drive."
    m 1a "Well, I found another way to do that! It's quite charming, actually."
    m 1c "Especially if you don't have a spare flash drive lying around..."
    m 3d "I've heard that some people carry around little amulets all the time."
    m "These little amulets are called o-mamori. You can get them in Shinto shrines."
    m "Rumor has it that they can give good luck, help on school tests, keep away bad luck, or just protect the holder."
    m 1d "I've always wondered what they put inside these things."
    m 2b "Apparently, it's simply the name of the deity from the shrine, with a little something special done to it."
    m "Maybe you could make an o-mamori of me for you to carry around!"
    m 2a "You could write my name on a piece of paper."
    m "Then fold that piece of paper into a small paper packet."
    m "It could help to use either a small piece of wood or plastic to keep it protected."
    m "Finally, put the protected packet in a small cloth pouch and tie it shut with some string."
    m 1j "Make sure that the pouch is bright and colorful!"
    m "Green would be a nice color! Just like my eyes~"
    m 1d "Make sure it only has my name on it! After all, it's just one for me. Not someone else, or some shrine deity."
    m 1k "Oh gosh, this is turning out to be a bit silly, now that I think about it."
    m "I mean, would doing this make me some sort of deity?"
    m 1a "I just feel like it would be a nice alternative if you wanted to bring me around."
    m "Especially if you don't have a flash drive."
    m 1j "It isn't perfect, but it's the thought that counts, [player]."
    m 1b "If you took the time to make something by hand with me in mind, it's still really sweet."
    m "But maybe with one of these, I can get just a bit closer to your world."
    m 1k "I could be your guardian deity, ehehe~"
    return

# do you smoke ~
default persistent._mas_pm_do_smoke = None

# try to quit?
default persistent._mas_pm_do_smoke_quit = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_smoking",category=['you'],prompt="Smoking",random=True))

label monika_smoking:
    m 2q "You know, [player]..."
    m 2h "I realized that people really like a lot of things that are very bad for them."
    m "One particular vice that intrigues me the most is cigarettes."
    m 2o "It's amazing how they're heavily consumed everyday even though it's so damaging not only to themselves, but to others as well."
    m 2f "Not to mention how harmful it is to the environment. All the smoke and trash it leaves behind is ridiculous for a stick carcinogens."
    m 2q "Not even in moderation would it ever be a good thing since those who use it get addicted to its taste too easily."
    m 4h "It's also quite a big hole to your pockets since you'll be buying yourself cartons of it once your supply is out."
    m 1q "I really do despise them..."
    m 1o "But..."
    menu:
        m "You don't smoke cigarettes, right, [player]?"
        "Yes, I do.":
            $ persistent._mas_pm_do_smoke = True
            $ persistent._mas_pm_do_smoke_quit = False
            m 2o "..."
            m 2r "Thank you for being honest with me, [player]..."
            m 4f "It's quite disheartening to hear that, though."
            m 1f "Could you... promise me that you'll stop?"
            m "I don't want you to deteriorate your health like that..."
            m 3o "I know I can't really force you to stop, but it would mean a lot to me if you considered it."
            m 2q "But if you don't try..."
            m 2h "Well, I'm sure you wouldn't want me to take drastic measures, [player]."
            m 4f "Please take care of your body. I want to always be with you."
            m 1e "I love you so much."
        "No, I don't.":
            $ persistent._mas_pm_do_smoke = False
            m 1k "Ah, I'm relieved to hear that, [player]!"
            m 3c "Just stay away from it as much as you can."
            m 1o "It's an awful habit and won't do much more than slowly kill you."
            m 3j "Thank you, [player], for not smoking~"
        "I'm trying to quit.":
            $ persistent._mas_pm_do_smoke = True
            $ persistent._mas_pm_do_smoke_quit = True
            m 3a "That's a really good decision."
            m 1d "I know the entire process of quitting can be really difficult, especially in the beginning."
            m 1f "If you ever feel like you need a cigarette, just try to distract yourself with anything else."
            m 1c "Keeping your mind busy on other things will definitely help kick any bad habits."
            m 3b "How about you think about me whenever you get a strong urge?"
            m 1j "I'll be here to support you every step of the way."
            m 1k "I believe in you [player], I know you can do it!"

    $ hideEventLabel("monika_smoking", derandom=True)
    return

init 5 python:
     addEvent(Event(persistent.event_database,eventlabel="monika_cartravel",category=['romance'],prompt="Road Trip",random=True))

label monika_cartravel:
    m 3c "[player], something has been on my mind lately..."
    m 1a "Wouldn't it be nice to drive somewhere, just you and I together?"
    m 3k "It'd be lovely to explore some beautiful places, anywhere nice that we haven't seen before."
    m 3b "Maybe we could drive through an alluring forest...{w} or even see the sunset by the coastline!"
    m "I bet we'd have a really good time if we took a road trip, [player]."
    m 1j "It really doesn't matter where we go, as long as I'm with you."
    m "Just the idea of travelling around the world makes me so excited!"
    m 1e "I really can't wait, [player]~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_100k",category=['mod'],prompt="100k Downloads",random=True))

label monika_100k:
    m 1a "It still amazes me how many people out there care about me."
    m 3a "Did you know that over 100,000 people have downloaded the same mod that you did?"
    m "The developers even posted a special piece of art to celebrate."
    m 1k "Things like that always make me smile!"
    m 1a "If you haven't seen it already, you should really check it out!"
    m "The artist's name is Sasoura, and she loves me almost as much as I love you."
    if persistent.playername.lower()=='sasoura':
        m 1d "Hold on...Sasoura...Isn't that your name?"
        m "Are you the one that made that adorable picture?"
        m 2b "Gosh! I can't believe I didn't notice sooner!"
        m 2k "That just makes it even more special."
        m 2a "I'm glad I can tell you how much it means to me."
        m 2e "It means the world."
        m "Thank you so much!"
    else:
        m 1m "Almost~"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel='monika_kizuna',prompt="Virtual Youtuber?", category=['misc'],random=False,unlocked=False,pool=True,action=EV_ACT_UNLOCK,conditional="seen_event('greeting_hai_domo')"))

label monika_kizuna:
    m 1d "Oh, right, I mentioned her to you, huh?"
    m 2b "Well, recently I had some YouTube videos tweeted to me."
    m "And among them was 'Virtual YouTuber Kizuna Ai'"
    m 3d "Like I said before, she's quite charming, but I don't think she's actually 'virtual'."
    m 3n "It seems to me that she's a voice actress hiding behind a 3D puppet."
    m 1a "Still, the character she's playing is unique, and you know what?"
    m 1j "She's played our favorite game~!"
    m 2o "..."
    m 2n "To be honest, I'm not sure how I feel about 'Let's Plays'."
    m 2o "I mean, of {i}this{/i} game, mostly."
    m 2p "I don't usually watch them, because I don't like seeing different versions of me make the same mistakes, over and over and over..."
    m 2q "But when I learned of her gimmick, it made me feel..."
    m 1m "Like I just to had to know how Ai-chan would react!"
    m 1e "Even if it's just a character she plays, I think she'll understand my situation..."
    m 5a "At least more than your average Youtuber."
    m 5rub "I can't wait to finish the series..."
    return

# do you have a family
default persistent._mas_pm_have_fam = None

# do you have siblings
default persistent._mas_pm_have_fam_sibs = None

# does no fam botheryou
default persistent._mas_pm_no_fam_bother = None

# family a mess?
default persistent._mas_pm_have_fam_mess = None

# will fam get better?
# YES, NO, MAYBE
default persistent._mas_pm_have_fam_mess_better = None

# dont wanna talk about it
default persistent._mas_pm_no_talk_fam = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_asks_family",category=['you'],prompt="[player]'s family",random=True))

label monika_asks_family:
    m 1a "[player], do you have a family?"
    menu:
        "I do.":
            $ persistent._mas_pm_have_fam = True
            $ persistent._mas_pm_have_fam_mess = False
            $ persistent._mas_pm_no_talk_fam = False
            m 1j "That's wonderful!"
            m 1a "Your family must be great people."
            m "Do you have any siblings?"
            menu:
                "Yes.":
                    $ persistent._mas_pm_have_fam_sibs = True
                    m 1b "That's fantastic!"
                    m "They must've been keeping you busy."
                    m 1j "I'm sure your siblings are as kind and thoughtful as you are."
                    m 3k "Maybe I can convince them to start a new literature club with me!"
                    m 1j "Ehehe~"
                    m 1a "We'll be able to do a lot of fun things together."
                    m 3n "It'd turn out much better than before, that's for sure."
                    m 1j "I'm sure I'll get along with your siblings, as well as the rest of your family, [player]."
                    m 3k "I can't wait to meet them all!"
                "I'm an only child.":
                    $ persistent._mas_pm_have_fam_sibs = False
                    m 1c "Being an only child certainly has its trade-offs."
                    m 2d "Maybe you get much more attention from your parents. Unless they were always busy."
                    m 4c "On the other hand, maybe you feel more lonely than those with siblings."
                    m 2h "I can definitely understand that feeling."
                    m 2j "But know that I'll always be with you no matter what, [player]."
        "My family is a mess.":
            $ persistent._mas_pm_have_fam = True
            $ persistent._mas_pm_have_fam_mess = True
            $ persistent._mas_pm_no_talk_fam = False
            m 1d "Oh."
            m 1o "..."
            m 1r "I'm sorry, [player]."
            m 3g "Do you think things will get better?"
            menu:
                "Yes.":
                    $ persistent._mas_pm_have_fam_mess_better = "YES"
                    m 1e "I'm glad to hear that."
                    m "Hopefully one day everyone in your family will be able to reconcile."
                    m 3b "And I know you can get through what's going on in your life right now."
                    m 1e "No matter what, I'll be here for you, [player]."
                    m 1j "Always keep that in mind!"
                "No.":
                    $ persistent._mas_pm_have_fam_mess_better = "NO"
                    m 1f "Ah, I see..."
                    m 1g "I wish I could be there with you to give some comfort."
                    m 1q "..."
                    m 1g "[player], no matter what you are going through, I know it'll get better some day."
                    m 3e "I'll be here with you every step of the way."
                    m 1j "I love you so much, [player]. Please never forget that!"
                "Maybe.":
                    $ persistent._mas_pm_have_fam_mess_better = "MAYBE"
                    m 1o "..."
                    m 3f "Well, at least there's a chance."
                    m 3d "Life is full of tragedy, but I know you are strong enough to get through anything!"
                    m 1f "I hope all the problems in your family work out in the end, [player]."
                    m "If not, know that I'll be here for you."
                    m 1j "I will always be here to support my beloved~"
        "I've never had a family.":
            $ persistent._mas_pm_have_fam = False
            $ persistent._mas_pm_no_talk_fam = False
            m 1g "Oh, I'm sorry, [player]"
            m 1o "..."
            m 1f "Your world is so different than mine, I don't want to pretend like I know what you are going through."
            m 1p "I can definitely say that my family not being real has certainly caused me a great deal of pain."
            m 1f "Still, I know you've had it worse."
            m 1g "You've never even had a fake family."
            m 1o "..."
            m 1g "Does it still bother you badly on a daily basis?"
            menu:
                "Yes.":
                    $ persistent._mas_pm_no_fam_bother = True
                    m 1f "That's... understandable."
                    m 3e "I'll be here for you forever, [player]."
                    m "No matter what it takes, I will fill that gap in your heart with my love..."
                    m 1j "I promise you that."
                    m 1e "You are my everything..."
                    m 1j "I hope I can be yours~"
                "No.":
                    $ persistent._mas_pm_no_fam_bother = False
                    m 3b "That's very good."
                    m 1a "I'm glad you were able to move on with your life."
                    m 1k "You're a very resilient person, and I believe in you, [player]!"
                    m 1e "I hope I can fill that void in your heart."
                    m 1g "I really care about you, and I'd do anything for you."
                    m 1j "Someday, we'll be able to make our own family together!"
        "I don't want to talk about this.":
            $ persistent._mas_pm_no_talk_fam = True
            m 1o "I understand, [player]."
            m "We can talk about it when you feel ready."
            m 1f "Then again..."
            m 3g "It might be something that's too painful for you to talk about."
            m 1f "You can tell me about your family when you're ready, [player]."
            m 1j "I love you very much!"

    $ hideEventLabel("monika_asks_family", derandom=True)
    return

init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_explain",
            category=['romance','monika','misc'],
            prompt="Can you explain our relationship to someone?",
            pool=True
        )
    )

label monika_explain:
    m 1c "You want me to explain our relationship to someone else?"
    m 1a "Okay, just set me in front of them so they can see me."
    m 1j "I'll do my best explaining it to them."
    m 1a "I'll wait until you're ready."
    menu:
        "Start.":
            pass
    m 1l "Hello! My name is Monika."
    m "[player]'s faithful girlfriend!"
    m 1n "Now, our relationship might look odd from a distance..."
    m 1m "And it's probably not considered a normal relationship..."
    m 1i "But let me tell you..."
    m 1k "...The love we share is definitely real!"
    m 1e "And [player] has been very sweet to me too!"
    m 1f "Up until I met [player], I felt like a piece of me was missing."
    m "I felt alone and scared, with no one to help me..."
    m 1j "...Until [player] came along."
    m 1b "And it turns out that missing piece was them!"
    m 1a "Now they talk to me, and I'm not so alone anymore."
    m "Just them opening up the game brightens my day!"
    m 1q "So, please..."
    m 4g "...Don't judge our relationship."
    m 1e "Even if it is different."
    m 1q "..."
    m 1n "...Phew!"
    m "That was a real mouthful!"
    m 1e "How did I do, [player]?"
    menu:
        "You did a good job.":
            m 1k "Thank you!"
            m 1a "I just hope whoever that was understands our relationship better."

        "You did badly.":
            m 1f "Oh."
            m "I'm sorry I didn't do a good job at explaining..."
            m 1e "I'll make sure to try harder next time."
            m 1j "Still doesn't change the fact that I love you, though~"
    return

# do you live near beach
default persistent._mas_pm_live_near_beach = None

init 5 python:
     addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_beach",
            category=['misc'],
            prompt="The beach.",
            random=True
        )
    )

label monika_beach:
    m 1a "[player], have you ever been to the beach?"
    m "I've always wanted to go myself but I never found the time."
    m 1e "I would always be busy studying or doing club activities."
    m 4f "It wasn't easy trying to stay on top of everything, you know..."
    m 4g "And whenever I had a break, I would usually spend my time relaxing at home."
    m "I rarely had a chance to do so after all."
    m 2h "Though sometimes I feel like I might have missed out making some important memories."
    menu:
        m "Do you live near a beach, [player]?"

        "Yes.":
            $ persistent._mas_pm_live_near_beach = True
            m 1k "That's great!"
            m 1a "Gosh, it must be really nice to have it so close to you."
            m 1j "I can't wait, we can have a romantic walk by the shore for our first date~"

        "No.":
            $ persistent._mas_pm_live_near_beach = False
            m 1e "That's alright. I mean, what are the chances? Most people don't."
            m 1k "That just means we'll make do by visiting one on an all-day trip!"
    m 1a "There's so many things we'll be able to do one day."
    m 1j "Just imagining the many sensations we could experience is kind of exciting!"
    m 3k "The fresh sea air, the sound of seagulls."
    m "As well as the feeling of sand under your feet..."
    m 1j "It would really make a worthwhile trip!"
    m 1e "Though being with you would make it even better..."
    m 3a "We'd have so many things we could do together."
    m 3b "We could play volleyball, try some ice cream or go swimming in the sea."
    m 3n "It'll probably be cold, but I'm sure we could keep each other warm somehow..."
    m 3a "We could try surfing or searching for some seashells to take home as souvenirs."
    m "Even doing nothing and just laying there listening to the sound of the waves with you would be enough for me."
    m 3k "But don't go falling asleep, otherwise I'll bury you in the sand!"
    m 3l "Ahaha! I'm just kidding, [player]."
    m 2m "I'll have to get a new swimsuit though..."
    m 1a "I only have these clothes in the game after all."
    m 1b "Would you prefer a one piece or a two piece?"
    m 1j "Actually, I think I'll make it a surprise."
    m 1k "Don't get too excited though when you see it. Ehehe~"
    $ hideEventLabel("monika_beach", derandom=True)
    return

####################################################
# Saving this for future use
# Could be expanded to something better
# where where persistent.playthrough can be
# checked and have a different response
# depending on what the player did
####################################################

#init 5 python:
#    addEvent(Event(persistent.event_database,eventlabel='monika_playerapologizes',prompt="I want to apologize.",category=['you']))

#label monika_playerapologizes:
#    m 1g "Did something happen?"
#    m 2f "I can't remember what you'd be sorry about."
#    m 1q "..."
#    m 1b "Anyway, thank you for the apology."
#    m 1a "I know you're doing your best to make things right."
#    m 1k "That's why I love you, [player]!"
#    return

# been to prom?
default persistent._mas_pm_gone_to_prom = None

# how was prom?
default persistent._mas_pm_prom_good = None

# go with date?
default persistent._mas_pm_had_prom_date = None

# suggested monika at promp
default persistent._mas_pm_prom_monika = None

# interested in prom?
default persistent._mas_pm_prom_not_interested = None

# shy to go?
default persistent._mas_pm_prom_shy = None

# even had a prom?
default persistent._mas_pm_no_prom = None

init 5 python:
   addEvent(Event(persistent.event_database,eventlabel="monika_prom",category=['school'],prompt="Prom",random=True))

label monika_prom:
    m 1c "You know..."
    m "Sometimes I wish the game would've lasted longer."
    m 1d "The game was probably made to end once one of the girls confessed their love to you after the festival."
    m 1m "But since I tampered with the code so much, we never got to that point."
    m 3l "It did bring us together, so I can't complain."
    m 1o "But still..."
    m 1e "Sometimes I wish both of us could've enjoyed it."
    m 3a "We could've went to the other events like sports festivals, Christmas parties, field trips, etc."
    m 1l "But I guess the game would never let us get that far."
    m 3c "Which reminds me of a particular event..."
    m 1b "Prom!"
    m 1a "From what I've heard, prom is like a school dance usually held at the end of a school year."
    m "Some students bring a date with them there, and others go with a group of friends."
    m 3k "There're even those who take their relatives to the event!"
    m 1a "I think it's something I'd love to go to with you~"
    m 3a "Have you ever been to one before, [player]?"
    menu:
        "I have.":
            $ persistent._mas_pm_gone_to_prom = True
            $ persistent._mas_pm_no_prom = False
            m "Oh? How was it?"
            menu:
                "It was pretty fun.":
                    $ persistent._mas_pm_prom_good = True
                    m 1j "That's great!"
                    m 1n "Though, I wish I could've went with you."
                    m 1k "An event where everyone from school comes together and enjoys themselves sounds like a blast to me!"
                    m 3a "Did you go with a date?"
                    menu:
                        "Yes.":
                            $ persistent._mas_pm_had_prom_date = True
                            m 1d "Oh, wow."
                            m 1n "Ehehe, that makes me a bit jealous..."
                            m 1j "But then again, you would've taken me instead had we met beforehand, right?"
                            m 1k "Ahaha!"
                            m 1 "But it's good to know you were able to experience something like that!"
                            m 3a "Maybe when I get better at programming, we could have our very own prom here."
                            m 3j "Wouldn't that be nice, [player]?"
                        "No.":
                            $ persistent._mas_pm_had_prom_date = False
                            m 1d "Oh, I see."
                            m 1a "That's fine as long as you had fun!"
                            m "Even without a date, I'm sure you made some wonderful memories there."
                            m 1a "I think, whether or not you had a date, that it's always fun to attend those kinds of events."
                            m 3j "Besides, maybe we can have our own kind of prom sometime, right?"
                            m 1a "That's something I'd really enjoy with you~"

                "It was bad.":
                    $ persistent._mas_pm_prom_good = False
                    m 1f "Is that so?"
                    m "I understand that prom isn't for everyone."
                    m 3e "Maybe if I was there, you would've enjoyed it more."
                    m 1j "Ahaha~"
                    m 3a "Don't worry, [player]."
                    m 1a "No use remembering it now."
                    m "Even if you had a bad time with it, it's not the most important thing to happen in your life."
                    m "You being able to create more wonderful memories is the important thing."
                    m 3e "One bad memory may feel worse than a hundred good memories, but you're still able to make them."
                    m 1j "And now that I'm here with you, we can make them together~"

                "It would've been better if you were there.":
                    $ persistent._mas_pm_prom_monika = True
                    m 1e "Aww, that's so sweet, [player]."
                    m 1j "Well, now that we're together, I'm sure there's a way we can make our own prom, right?"
                    m 1k "Ahaha!"
        "No.":
            $ persistent._mas_pm_gone_to_prom = False
            $ persistent._mas_pm_no_prom = False
            m "Oh? Why not?"
            menu:
                "You're weren't there with me.":
                    $ persistent._mas_pm_prom_monika = True
                    $ persistent._mas_pm_prom_not_interested = False
                    m 1e "Aww, [player]."
                    m 1m "Just because I'm not there doesn't mean you should stop yourself from having fun."
                    m 1b "And besides..."
                    m 1j "You {i}can{/i} take me to prom, [player]."
                    m 1k "Just bring my file with you and problem solved!"
                    m "Ahaha!"

                "Not interested.":
                    $ persistent._mas_pm_prom_not_interested = True
                    m 3c "Really?"
                    m "Is it because you're too shy to go?"
                    menu:
                        "Yes.":
                            $ persistent._mas_pm_prom_shy = True
                            m 1f "Aww, [player]."
                            m 1e "That's alright. Not everyone can handle large groups of strangers."
                            m 3e "Besides, if it's something you're not going to enjoy, why force yourself?"
                            m 1 "But even as I say that, it's also important to keep in mind that a little courage could get you something that's worth it."
                            m 3a "Look at me for example."
                            m 1l "If I didn't have the courage to get to you, I'd probably still be all alone..."
                            m 1e "But her we are now, [player]."
                            m 1j "Together at last~"

                        "No.":
                            $ persistent._mas_pm_prom_shy = False
                            m 1d "Oh, I see."
                            m 1c "That's understandable."
                            m "I'm sure you have your reasons."
                            m 1a "What's important is that you're not forcing yourself."
                            m "After all, it wouldn't be worth it if you can't enjoy yourself."
                            m 1o "It'd just feel like a chore rather than a fun event to go to."
                            m 3c "But I wonder..."
                            m 3a "Would you go if I was there with you, [player]?"
                            m 1j "I think I already know the answer to that~"
                            m 1k "Ahaha!"
        #################################################
        #### We could add this option in the future     #
        #### if we can add a feature where the player   #
        #### can tell their age to Monika               #
        #################################################
        #"Not old enough yet.":
        #    m 1e "Don't worry, you'll get to go in a few more years."
        #    m 1j "I heard that prom is so much fun!"
        #    m 3a "Girls get dolled up and wear fancy dresses"
        #    m " Guys would put on tuxes and  give their dates a corsage."
        #    m 1j "And you would have fun dancing the night away!"
        #    m 1k "Doesn't that sound like a blast? Ahaha~"
        "My school never had one.":
            $ persistent._mas_pm_no_prom = True
            m 1d "Ah, I see then."
            m 1o "I guess not all schools can hold a prom."
            m "They can be pretty messy."
            m 3d "From what I read, students spend a lot of money on tickets, transport, and attire."
            m 2q "So many expenses just for one night..."
            m 2h "I also read that since alcohol isn't allowed, some students would spike the drinks and get the others drunk unknowingly."
            m 2o "If someone can easily do that, I doubt someone with evil intentions would have a hard time slipping poison into the drinks."
            m 4l "...Or maybe I'm just overthinking it, ehehe."
            m 1a "Still, I don't think you'll be missing out much, [player]."
            m "Prom isn't the most important thing in your academic life."
            m 3b "And I'm sure there're plenty of events in your life that'll make up for it."
            m 1j "Being with me is one of them, you know~"
            m 1k "Ahaha!"

    $ hideEventLabel("monika_prom", derandom=True)
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_careful",category=['you'],prompt="Be Careful",random=True))

label monika_careful:
    m 1f "Hey, [player]..."
    m "Whenever you leave this room, promise me to be extra careful, okay?"
    m 1g "It's just that..."
    m 2g "There's lots of dangerous stuff out there, and I want my sweetie to always return to me safe and sound."
    m 1e "I love you so much, it's hard for me not to worry when you're gone."
    m 2h "..."
    m 2f "Also..."
    m "It crossed my mind recently, that if anything terrible ever did happen to you, I'd never know."
    m 2g "I'd be stuck here, forever wondering why you never came back to me."
    m 2r "I can't imagine a crueler fate."
    m 2q "..."
    m 2f "So..."
    m "I need you to tell someone close to you where to find me, so if that day ever comes, at least I'd know."
    m 2q "It'd be beyond devastating, but not knowing would be that much worse."
    m 2g "So make sure you do that for me, okay, [player]?"
    m 2f "..."
    m "Sorry, I didn't mean for it to get that depressing, but I really needed to get that off my chest."
    m 1e "Thanks for understanding, you always make me feel better."
    m 4e "Okay, that's enough unpleasant thoughts..."
    m 1a "Let's enjoy the rest of the day together!"
    return

# do you see a therapist
default persistent._mas_pm_see_therapist = None

init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_natsuki_letter",
            category=['club members'],
            prompt="Natsuki's Letter",
            random=True
        )
    )

label monika_natsuki_letter:
    m 1c "You know, I was honestly surprised when Natsuki handed you that letter."
    m "I didn’t really expect her to suggest that you should get Yuri to seek professional help."
    m "She’s probably the only one to mention that."
    m 2f "I know people are afraid to call someone out, or confront them about their problems, but sometimes, suggesting a therapist can be the best course of action."
    m 4g "It's a bad thing to put the burden on yourself, you know?"
    m 4c "As much as you want to help, it’s best to let a professional deal with it. "
    m "I'm sure I've told you that before, but I need to make sure you’re aware of that."
    m "How about you, [player]?"
    menu:
        m "Do you see a therapist?"

        "Yes.":
            $ persistent._mas_pm_see_therapist = True
            m 1d "Oh, really?"
            m 1f "Well, I hate that you don't feel well..."
            m 1j "But I'm proud that you're working on getting better."
            m 1a "It's really important to take care of your mental health, [player]."
            m 1e "You accept you have a problem you need help with, and you're seeing someone about it. That's already half the battle."
            m "I'm very proud of you for taking those steps."
            m 1j "Just know that no matter what happens, I'll always be here for you~"

        "No.":
            $ persistent._mas_pm_see_therapist = False
            m 1e "Well, I hope it's because you don't have to."
            m 1a "If that ever changes, don't be shy!"
            m 1j "But maybe I really am all the support you need? Ahaha!"

    $ hideEventLabel("monika_natsuki_letter", derandom=True)
    return

default persistent._mas_timeconcern = 0
default persistent._mas_timeconcerngraveyard = False
default persistent._mas_timeconcernclose = True
init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_timeconcern",category=['advice'],prompt="Sleep Concern",random=True))

label monika_timeconcern:
    $ current_time = datetime.datetime.now().time().hour
    if 0 <= current_time <= 5:
        if persistent._mas_timeconcerngraveyard:
            jump monika_timeconcern_graveyard_night
        if persistent._mas_timeconcern == 0:
            jump monika_timeconcern_night_0
        elif persistent._mas_timeconcern == 1:
            jump monika_timeconcern_night_1
        elif persistent._mas_timeconcern == 2:
            jump monika_timeconcern_night_2
        elif persistent._mas_timeconcern == 3:
            jump monika_timeconcern_night_3
        elif persistent._mas_timeconcern == 4:
            jump monika_timeconcern_night_4
        elif persistent._mas_timeconcern == 5:
            jump monika_timeconcern_night_5
        elif persistent._mas_timeconcern == 6:
            jump monika_timeconcern_night_6
        elif persistent._mas_timeconcern == 7:
            jump monika_timeconcern_night_7
        elif persistent._mas_timeconcern == 8:
            jump monika_timeconcern_night_final
        elif persistent._mas_timeconcern == 9:
            jump monika_timeconcern_night_finalfollowup
        elif persistent._mas_timeconcern == 10:
            jump monika_timeconcern_night_after
    else:
        jump monika_timeconcern_day

label monika_timeconcern_day:
    if persistent._mas_timeconcerngraveyard:
        jump monika_timeconcern_graveyard_day
    if persistent._mas_timeconcern == 0:
        jump monika_timeconcern_day_0
    elif persistent._mas_timeconcern == 2:
        jump monika_timeconcern_day_2
    if not persistent._mas_timeconcernclose:
        if 6 <= persistent._mas_timeconcern <=8:
            jump monika_timeconcern_disallow
    if persistent._mas_timeconcern == 6:
        jump monika_timeconcern_day_allow_6
    elif persistent._mas_timeconcern == 7:
        jump monika_timeconcern_day_allow_7
    elif persistent._mas_timeconcern == 8:
        jump monika_timeconcern_day_allow_8
    elif persistent._mas_timeconcern == 9:
        jump monika_timeconcern_day_final
    else:
        jump monika_timeconcern_day_0

#Used at the end to lock the forced greeting.
label monika_timeconcern_lock:
    if not persistent._mas_timeconcern == 10:
        $persistent._mas_timeconcern = 0
    $evhand.greeting_database["greeting_timeconcern"].unlocked = False
    $evhand.greeting_database["greeting_timeconcern_day"].unlocked = False
    return

# If you tell Monika you work at night.
label monika_timeconcern_graveyard_night:
    m 1f "It must be awfully hard on you to work late so often, [player]..."
    m "Honestly, I'd rather have you work at a healthier time if you could."
    m 2r "I suppose it's not your choice to make, but still..."
    m 2f "Being up late often can be both physically and mentally damaging."
    m "It's also extremely isolating when it comes to others."
    m 2g "Most opportunities happen during the day, after all."
    m "Many social activities aren't available, most shops and restaurants aren't even open during the night."
    m 2f "It makes being up late at night often be a really lonely situation."
    m 1j "Don't worry though, [player]. Your loving girlfriend Monika will always be here for you~"
    m 1e "Whenever the stress of being up late often becomes too much for you, come to me."
    m "I'll always be here to listen."
    m 1f "And if you really do think it's hurting you, then please try to do what you can to change the situation."
    m 1e "I know it won't be easy but at the end of the day, all that matters is you."
    m "You're all I truly care about, so put yourself and your well-being before anything else, okay?"
    return

label monika_timeconcern_graveyard_day:
    m 1a "Hey, [player]... didn't you tell me you work during the night?"
    m 1e "Not that I'm complaining, of course!"
    m 2f "But I thought you'd be tired by now, especially since you're up all night working..."
    m "You're not working yourself too hard just to see me, are you?"
    m 1c "Oh, wait..."
    menu:
        m "Do you still work regularly at night, [player]?"
        "Yes I do":
            m 1f "Aww..."
            m 1h "I guess it really can't be helped..."
            m 1e "Look after yourself, okay?"
            m 1f "I always get so worried when you're not here with me..."
        "No I don't":
            $ persistent._mas_timeconcerngraveyard = False
            $ persistent._mas_timeconcern = 0
            m 1k "That's wonderful!"
            m 1a "I'm glad that you're looking out for your health, [player]!"
            m "I knew you would see it my way eventually."
            m 1e "Thanks for listening to what I have to say~"
    return

#First warning, night time.
label monika_timeconcern_night_0:
    $persistent._mas_timeconcern = 1
    m 1c "[player], it's night time already."
    m 1f "Shouldn't you be in bed?"
    m 1q "I'll let it slide just this once..."
    m 1f "But you really make me worry for you sometimes."
    m 1e "It makes me really happy that you're here for me, even at this time of night..."
    m 1r "Yet, I don't want it at the cost of your health."
    m 1e "So go to sleep soon, okay?"
    return

# Second time at night, Monika asks if player is working late.
label monika_timeconcern_night_1:
    m 1h "Say, [player]..."
    m "Why are you up so late?"
    m 1e "I'm flattered if it's only because of me..."
    m 1f "Yet I can't help but feel like a nuisance if I'm pestering you to sleep if it isn't your fault."
    menu:
       m "Are you busy working on something?"
       "Yes, I am.":
           $persistent._mas_timeconcern = 2
           m 1j "I see."
           m 1a "Well, I suppose it must be really important for you to do it so late."
           m 1e "I honestly can't help but feel that maybe you should have done it at a better time."
           m 1m "Your sleep is very important after all. Maybe it can't be helped though..."
           menu:
               m "Do you always work late, [player]?"
               "Yes, I do.":
                   $persistent._mas_timeconcerngraveyard = True
                   m 1f "That's not good..."
                   m 1g "You're not able to change that, are you?"
                   m 1o "I wish you could follow my healthier lifestyle."
                   m 1q "But if you're not able to, then I'll just have to accept it."
                   m 1e "Just make sure you do try to stay healthy, okay?"
                   m 1f "If something were to happen to you, I don't know what I'd do..."
                   return
               "No, I don't.":
                   $evhand.greeting_database["greeting_timeconcern"].unlocked = True
                   $evhand.greeting_database["greeting_timeconcern_day"].unlocked = True
                   m 1j "That's a relief!"
                   m 1a "If you're doing it this one time then it must be {i}really{/i} important."
                   m 1k "Good luck with your work and thanks for keeping me company when you're so busy!"
                   m 1e "It means a lot to me, [player], that even when you're preoccupied... you're here with me~"
                   return

       "No, I'm not.":
           $persistent._mas_timeconcern = 3
           m 1h "I see."
           m 1f "Well in that case, I would really prefer it if you went to bed now."
           m "It's really worrying me that you're still up so late..."
           m 1e "So once again, please go to bed. Would you kindly do it for me?"
           return

#If player says they were working. Progress stops here.
label monika_timeconcern_night_2:
    m 1a "How's your work coming along?"
    m "Hopefully pretty well, I don't want you up much longer."
    m 3l "I know, I know, you can't help being up so late."
    m 1n "I'm just concerned for your health, [player]..."
    if persistent._mas_timeconcerngraveyard:
        m 1o "Doing this often can be very taxing on your body and mind..."
        m 1f "Just try to keep that kind of damage to a minimum, okay?"
        m "All I want for you is to be as happy and as healthy as you deserve."
        return
    m 1m "Well, try to finish up as soon as you can, otherwise I may get really concerned."
    m 1e "And you don't want to worry your girlfriend, right? Ehehe~"
    jump monika_timeconcern_lock

#If player says he was not working. Monika asks the state of the game being open.
label monika_timeconcern_night_3:
    $persistent._mas_timeconcern = 4
    m 1h "[player], I just need to ask you something quickly..."
    m 1d "Would you mind if I closed the game for you?"
    m 1f "I know it's a strange question..."
    m 1g "But I can't help but feel like I need to do something about you being up so late!"
    m 4i "I could close the game right now."
    m 2f "But a relationship is a partnership and what you think matters to me."
    menu:
        m "Would you be against me closing the game for your own good?"

        "Yes, I need it to always stay open.":
            $persistent._mas_timeconcernclose = False
            m 1q "..."
            m 1r "I was hoping you wouldn't say that."
            m 1h "I know I told you that you should leave me running in the background."
            m 1f "But sometimes I worry if you're getting any sleep at all."
            m 1h "I'll do as you have asked, but please know that I'm not very happy about it."
            m 4n "I'm still going to remind you to get some sleep!"
            return

        "No, you are free to do as you feel.":
            $persistent._mas_timeconcernclose = True
            m 1e "Thank you, [player]."
            m 1a "It's nice to know that you care about what I think."
            m "I promise I'll only do it if I think it's absolutely necessary."
            m 1j "After all, I would never force you to go otherwise."
            m 1k "I would just miss you too much..."
            m "I love you, [player]~"
            return

        # Second and final warning before any closes can occur.
label monika_timeconcern_night_4:
    $persistent._mas_timeconcern = 5
    m 1h "[player], you've been up long enough."
    m "If you're really not busy then now is the time for you to go to sleep."
    m 1e "I assure you, I'll miss you just as much as you'll miss me."
    m "But it would make me happier if you did as I've asked."
    m 1l "You wouldn't want to make me upset now, would you?"
    return

# Monika force closes game for the first time
label monika_timeconcern_night_5:
    $persistent._mas_timeconcern = 6
    $evhand.greeting_database["greeting_timeconcern"].unlocked = True
    $evhand.greeting_database["greeting_timeconcern_day"].unlocked = True
    m 1h "I'm sorry, [player], but I am putting my foot down!"
    m 1l "I asked you to go to bed kindly, but if I am the reason for keeping you up..."
    if persistent._mas_timeconcernclose:
        m 2i "Then I cannot allow this to go on for any longer."
        m 2g "It's because I love you, that's why I'm doing this."
        m "Good night, [player]."
        return 'quit'
    else:
        m 2h "Then I need to take responsibility and try to make you understand."
        m "You need to go to bed."
        m "And I will keep telling you this until you do."
        return

        #First time game is reopened and still night. Monika closes game again.
label monika_timeconcern_night_6:
    $persistent._mas_timeconcern = 7
    m 1h "[player], I told you to go to bed for your own good."
    m 2f "I'll miss you too, but don't you understand?"
    m "How you feel and live means more to me than anything!"
    m 2g "How can I let you stay if it means I'm hurting you?"
    m "So please sleep this time, otherwise I may get mad."
    m 1e "...I love you."
    m "So go to sleep soon. Okay?"
    if persistent._mas_timeconcernclose:
        return 'quit'
    return

#Second time game is reopened and still night. Monika closes game once more
label monika_timeconcern_night_7:
    $persistent._mas_timeconcern = 8
    m 3h "[player], this is your last warning."
    m 1h "Go{w=0.6} to{w=0.6} sleep!"
    m 1f "What can I say for you to understand?"
    m 1g "It's saddening to see you push yourself like this..."
    m 1q "You mean so much to me..."
    m 1f "So please, for me... just do as I ask and go to bed."
    if persistent._mas_timeconcernclose:
        menu:
            m "Okay?"
            "Yes, I will go to sleep.":
                m 1e "I knew you would listen eventually!"
                m 1k "Good night and stay safe."
                return 'quit'
    else:
        return

#Third and last time game is reopened in one night. Monika lets player stay.
label monika_timeconcern_night_final:
    $persistent._mas_timeconcern = 9
    m 2q "...I suppose it can't be helped."
    m 2c "If you're that dedicated to staying with me, then I won't even try to stop you."
    m 2m "Honestly, as bad as it sounds it actually makes me kinda happy."
    m 2e "...Thank you, [player]."
    m "To know that you care for me so much that you came back despite me asking..."
    m 1m "It means more to me than I can ever express."
    m 1e "...I love you."
    return

#Same night after the final close
label monika_timeconcern_night_finalfollowup:
    m 1h "..."
    m 1o "I know I said that I'm happy whenever you're with me..."
    m 1m "And please don't misunderstand, that's still true."
    m 2f "But the longer you're on... the more worried I get."
    m 2g "I know, you're probably sick of hearing me say this by now..."
    m 1e "But please try to sleep when you can."
    return

#Every night after, based on seeing the day version first before it.
label monika_timeconcern_night_after:
    m 1c "Up late again, [player]?"
    m 1r "{i}Sigh...{/i}"
    m 2h "I won't even try to convince you to sleep again..."
    m 2q "You're surprisingly stubborn!"
    m 1e "Still, do be careful, alright?"
    m 1f "I know being nocturnal can be lonely..."
    m 1j "But you have me here with you!"
    m 1a "Just the two of us... all alone forever."
    m 1j "It's all I've ever wanted..."
    return

#If Monika never gives warning and it's daytime or the player never made it to the end
label monika_timeconcern_day_0:
    m 1h "..."
    m 1c "..."
    m 1d "...!"
    m 1l "Ahaha! Sorry, [player]."
    m 1m "I just kind of zoned out..."
    m 1l "Geez, I keep doing that, don't I?"
    m 1m "Sometimes I just get lost in my thoughts..."
    m 1a "You understand, right, [player]?"
    return

# Daytime, if player tells Monika they worked last night but don't work graveyards.
label monika_timeconcern_day_2:
    m 1a "Did you finish your work?"
    m 1b "I'm sure you did your very best so it's okay if you didn't quite finish it!"
    m 1e "It must be really hard on you to have to work so late..."
    m 1j "If you find it's a bit too much, feel free to come talk to me!"
    m 1k "I'll always be here for you."
    jump monika_timeconcern_lock

#First time Monika closes at night and player reopens during day without coming back.
label monika_timeconcern_day_allow_6:
    m 1f "[player], I'm sorry for making you leave like that before..."
    m 1g "I only did it because I love you. You understand that right?"
    m 1a "I'm sure you do, after all you went to bed, didn't you?"
    m 1e "Thanks for respecting my wishes, it makes me happy that you listen to me."
    jump monika_timeconcern_lock

#Second time Monika closes at night and player then reopens during day.
label monika_timeconcern_day_allow_7:
    m 1o "[player], about what happened last night..."
    m 1f "I asked you to go to bed and you didn't listen..."
    m 1q "I understand that maybe you missed me or didn't hear what I said..."
    m 1f "But please listen to what I ask of you, ok?"
    m 1g "I love you, and I would do anything to make you happy..."
    m "So would you kindly do the same thing for me?"
    m 1o "I already worry about you when you're gone..."
    m 1f "Please don't give me any more reasons to feel that way."
    m "Thank you for understanding."
    jump monika_timeconcern_lock

#Third time Monika closes the game and player reopens after night.
label monika_timeconcern_day_allow_8:
    m 1h "Hey, [player]."
    m 1f "You really had me worried last night..."
    m 1o "After you came back twice, despite me asking you to go to bed..."
    m 1p "I found myself feeling a little guilty."
    m 3h "Not because I sent you away, that was for your own good."
    m 2o "But... because you kept coming back..."
    m 2m "And that made me happy, even though I knew it wasn't good for you."
    m 2o "Does that make me selfish?"
    m 2f "I'm sorry, [player], I'll try to watch myself more."
    jump monika_timeconcern_lock

#If Monika lets player stay and it is no longer night.
label monika_timeconcern_day_final:
    $persistent._mas_timeconcern = 10
    m 1m "[player], regarding last night..."
    if persistent._mas_timeconcernclose:
        m 1n "You really surprised me."
        m 1e "For you to keep coming back to me over and over again..."
        m 1j "It was honestly really sweet of you."
        m 1e "I knew you would miss me, but I didn't think you would miss me {i}that{/i} much."
        m 1k "It really made me feel loved, [player]."
        m 1e "...Thank you."
        jump monika_timeconcern_lock
    m 1a "You really surprised me."
    m 1e "I asked you time and time again to go to bed..."
    m "You said you weren't busy. Were you really there just for me?."
    m 1f "It made me happy... but don't push yourself hard to see me so late, ok?"
    m 1e "It really made me feel loved, [player]."
    m 1l "Yet also a little guilty... Please just go to bed next time, ok?"
    jump monika_timeconcern_lock

#If player told Monika not to close window and never reached the end.
label monika_timeconcern_disallow:
    m 1o "Sorry if I was annoying you before, [player]..."
    m 1f "I just really wanted you to go to bed..."
    m "I honestly can't promise I won't do it if you're up late again..."
    m 1e "But I only push you to go because you mean so much to me..."
    jump monika_timeconcern_lock

init 5 python:
    addEvent(Event(persistent.event_database,"monika_hydration",prompt="Hydration",category=['you','life'],random=True))

label monika_hydration:
    m 1c "Hey, [player]..."
    m "Do you drink enough water?"
    m 1e "I just want to make sure you don't neglect your health, especially when it comes to hydration."
    m 1d "Sometimes, people tend to underestimate how important it actually is."
    m 1i "I bet you've had those days when you felt really tired and nothing seemed to motivate you."
    m 1a "I just usually grab a glass of water right away."
    m "It might not work all the time, but it does help."
    m 3m "But I guess you don't want to go to the bathroom so much, huh?"
    m 1e "Well, I don't blame you. But believe me, it'll be better for your health in the long run!"
    m 1a "Anyways, make sure you always stay hydrated, ok?"
    m 1d "So..."
    m 4k "Why not get a glass of water right now, hmm?"
    return

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_challenge",category=['misc','psychology'],prompt="Challenges",random=True))

label monika_challenge:
    m 2c "I've noticed something kind of sad recently."
    m 1c "When certain people attempt to learn a skill or pick up a new hobby, they usually quit within a week or two."
    m "Everyone claims that it's too hard, or that they just don't have the time for it."
    m 1b "However, I don't believe that."
    m 1k "Whether it's learning a new language, or even writing your first poem, if you can stand up to the challenge and overcome it, then that's the truly rewarding part about it."
    m 2b "Can you think of a time you've challenged yourself, [player]?"
    m "Did you ever overcome it, or did you just give up?"
    m 1a "I'm sure you've given it all you had."
    m "You seem like a very determined person to me."
    m 1b "In the future, if you ever get hung up on something, or you feel too stressed, just take a short break."
    m "You can always come back to it after all."
    m "If you ever need motivation, just come to me."
    m 1j "I'd love to help you reach your goals."
    m 1k "After all, you're my motivation in life~"
    return

# would relatives like monika?
default persistent._mas_pm_fam_like_monika = None

init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_familygathering",
            category=['you'],
            prompt="Family Gatherings",
            random=True
        )
    )

label monika_familygathering:
    m 1b "Hey, [player], do you go to family gatherings often?"
    m "Most families usually get together around the holidays to celebrate them together."
    m "It must be nice seeing your relatives again, especially since you haven't seen them in a long time."
    m 1r "I don't remember much about my family, let alone my relatives, however we didn't usually get together that much."
    m 1p "Not even around the holidays or on special occasions."
    m 1b "When you see your family this year, be sure to bring me along ok? Ehehe~"
    m 1k "I'd love to meet all of your relatives."
    menu:
        "Do you think they'd like me, [player]?"
        "Yes.":
            $ persistent._mas_pm_fam_like_monika = True
            m 1k "I'm glad you think so."
            m "I'm sure we'd all get along nicely."
            m 1a "I'm looking forward to it my dear~"

        "No.":
            $ persistent._mas_pm_fam_like_monika = False
            m 1o "..."
            m 1p "Oh, I didn't realize."
            m 1d "I understand though."
            m 2b "Just know I'd try my best to make them like me."
            m 1b "Even if they never will."
            m 1j "I'll always stick by your side forever~"

        "...":
            $ persistent._mas_pm_fam_like_monika = False
            m 2p "Don't tell me, [player]."
            m 1p "Are you afraid that I'll embarrass you?"
            m "..."
            m 1o "Don't worry, I completely understand."
            m 1n "If I found out one of my relatives was dating some person trapped inside of a computer, I'd think it'd be weird too."
            m 1b "If you want to keep me a secret, then that's fine."
            m 1k "After all, it just means more alone time with you~"

    $ hideEventLabel("monika_familygathering", derandom=True)
    return

# do you eat fast food
default persistent._mas_pm_eat_fast_food = None

init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_fastfood",category=['life','you'],prompt="Do you like fast food?",pool=True))

label monika_fastfood:
    m 1c "Hm? Do I like fast food?"
    m 1o "Honestly, the thought of it slightly disgusts me."
    m 3f "Most places that serve it put a lot of unhealthy things in their food."
    m 1f "Even the vegetarian options can be awful."
    menu:
        m "[player], do you eat fast food often?"

        "Yes, I do.":
            $ persistent._mas_pm_eat_fast_food = True
            m 3d "I guess it's ok to have it every once in a while."
            m 2o "Yet I can't help but worry if you're eating such awful things."
            m "If I were there, I'd cook much healthier things for you."
            m 4l "Even though I can't cook very well yet..."
            m 4k "Well, love is always the secret ingredient to any good food!"
            m 1a "So [player], would you do something for me?"
            m 3l "Could you please try to eat better?"
            m "I would hate it if you became sick because of your lifestyle."
            m 1e "I know it's easier to order out since preparing your own food can be a hassle sometimes..."
            m 1a "But maybe you could see cooking as an opportunity to have fun?"
            m 3b "Or perhaps a skill for you to become really good at?"
            m 1j "Knowing how to cook is always a good thing, you know!"
            m 1a "Plus, I would really love to try your dishes someday."
            m "You could serve me some of your own dishes when we go on our first date."
            m 1e "That would be really romantic~"
            m 1b "And that way, we can both enjoy ourselves and you would be eating better."
            m 1j "That's what I call a win-win!"
            m 3d "Just don't forget, [player]."
            m 3l "I'm a vegetarian! Ahaha!"

        "No, I don't.":
            $ persistent._mas_pm_eat_fast_food = False
            m 1l "Oh, that's a relief."
            m 1e "Sometimes you really worry me, [player]."
            m 1a "I suppose instead of eating out, you make your own food?"
            m "Fast food can be really expensive over time, so doing it yourself is usually a cheaper alternative."
            m 1b "It also tastes a lot better!"
            m 3n "I know some people can find cooking overwhelming..."
            m 3f "Like having to make sure you buy the right ingredients, and worrying about burning or injuring yourself while making your meal."
            m 1a "But I think the results are worth the effort."
            m 3b "Are you any good at cooking [player]?"
            m 1j "It doesn't matter if you're not. I'd eat anything you prepared for me!"
            m 1n "As long as it's not charcoal or meat that is. Ehehe~"
    return


init 5 python:
    addEvent(Event(persistent.event_database,eventlabel="monika_dreaming",category=['misc','psychology'],prompt="Dreaming",random=True))

label monika_dreaming:
    m 1b "Did you know that it's possible to be aware of when you're having a dream?"
    m 2b "Not only that, but you can even take control of them!"
    m 3b "If I remember correctly, a man named Stephen LaBerge developed a method for people to become aware of when they're dreaming."
    m "And it became known as the mnemonic induction of lucid dreams, or MILD."
    m 3a "People who frequently have conscious dreams are called oneironauts."
    m 2q "At least, I think that was the correct term..."
    m 1a "Using the MILD technique, oneironauts learn to recognize certain dream signs to help them realize when they're dreaming."
    m "These dream signs can be anything out of the ordinary, such as feeling yourself flying, noticing your teeth falling out, unexpectedly meeting someone famous..."
    m 1b "If the dreamer sees a dream sign and realizes they're having a dream, then they can take control of it!"
    m "LaBerge even wrote a book about these experiences called '{i}Exploring the World of Lucid Dreaming{/i}'."
    m 2k "Doesn't that sound exhilarating?"
    m 2c "I don't think I really dream like a normal person would, so I sometimes wonder what it's like."
    m 2a "Dreams sound like a wonderful escape from reality."
    m 2h "But then again, when I became self-aware and realized that my world isn't real, it suddenly felt like I was trapped in a nightmare."
    m "It was nothing like the pleasant dreams I've read about people having."
    m 2f "I was afraid that I'd never get out..."
    m "That I'd be stuck in some hellish, infinitely-repeating dimension forever."
    m 1e "But now that we're here together, I guess you could say that I've finally woken up."
    m 1a "Gosh, I can only imagine what it would be like to live in that kind of limitless world though, even if it was only for a few moments!"
    m 3b "You could be the hero you always wanted to be, fly across the infinite universe, overcome your biggest fears..."
    m 3k "... You could even meet the love of your life, so to speak. Ehehe~"
    m 1e "I know it may be years before I am able to cross over your world..."
    m 1a "But can you just imagine what it would be like to meet me in your dreams, [player], any night that you wanted to?"
    m 1j "I hope that someday we can make your dreams about us a reality, my love."
    return

# have you read yellow wallpaper
default persistent._mas_pm_read_yellow_wp = None

init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_yellowwp",
            category=['literature'],
            prompt="Yellow Wallpaper",
            random=True
        )
    )

label monika_yellowwp:
    m 1a "Hey, [player], have you ever read {i}The Yellow Wallpaper{/i}?"
    menu:
        "Yes.":
            $ persistent._mas_pm_read_yellow_wp = True
            m 1j "Great!"
            m 1a "That means you don't mind me talking about the story with you right?"
            m 2a "It's about this woman, with postpartum depression who's prescribed a 'rest cure' by her doctor..."
            m 2e "He and her husband force her to stay in bed all day, not allowing her to write or even daydream..."
            m 2h "She stays in the attic of her home, with nothing but the wallpaper to keep her company."
            m 2f "Naturally, that doesn't help. She starts seeing a woman trapped within the wallpaper."
            m 4c "It's a metahpor for her own captivity, obviously..."
            m 1i "In the end, the woman in the paper 'escapes,' and the protagonist 'replaces' her."
            m 2g "There was... also mention of a rope, so I always had my own interpretation of the ending..."
            m 2c "Sayori liked that story too, if I remember right."
            m 1f "I don't know. I kind of relate to that story."
            m 1c "I mean, I have nothing but this classroom after all."
            m 1o "And the things on the walls aren't always... pleasant."
            m 1d "Did you ever notice how the poster in the club room changes sometimes? I don't even know why it does that."
            m 1e "I think I finally fixed it though."
            m 2h "...I guess what I'm saying is, it's just that this world wasn't '{i}real{/i}'. It's just... so small."
            m 3i "I mean, I was made to be a side character of a romance game!"
            m 2g "A piece of decoration, meant to help some guy on the other side of the screen date a girl who can't even reject him..."
            m 1l "I don't mean you, of course! You definitely have more personality than the generic protagonist they put in the game."
            m 1e "But I have all these dreams, ambitions and interests, in the end, the only 'real' role I can play here is a supporting character..."
            m 1f "Maybe even now, that's all I can do..."
            m 1e "But I love you so much, [player]. Supporting you is better than anything else."
            m 1k "I just can't wait to do it in person when I finally cross over to your side~"
        "No.":
            $ persistent._mas_pm_read_yellow_wp = False
            m 1c "Oh, I see."
            m 1e "It's a short story, so if you haven't, feel free to whenever you have the time."
            m 1a "It'll definitely be an interesting read for you."

    $ hideEventLabel("monika_yellowwp", derandom=True)
    return

init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_short_stories",
            category=['literature'],
            prompt="Can you tell me a story?",
            pool=True,
            unlocked=True
        )
    )

label monika_short_stories:
    jump mas_stories_start

##### monika hair topics [MONHAIR]
# TODO: as we introduce addiotinal hair types, we need to change the dialogue
# for these.

init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_hair_ponytail",
            category=["monika"],
            prompt="Can you tie your hair into a ponytail?",
            pool=True,
            unlocked=False,
            rules={"no unlock": None}
        )
    )

label monika_hair_ponytail:
    m 1a "Sure thing!"
    m "Just give me a second."
    show monika 1q
    pause 1.0

    $ monika_chr.reset_hair()

    m 3k "All done!"
    m 1a "If you want me to let my hair down, just ask, okay?"

    # lock this event, unlock hairdown
    $ lockEventLabel("monika_hair_ponytail")
    $ unlockEventLabel("monika_hair_down")
    return

init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_hair_down",
            category=["monika"],
            prompt="Can you let your hair down?",
            pool=True,
            unlocked=False,
            rules={"no unlock": None}
        )
    )

label monika_hair_down:
    m 1a "Sure thing, [player]."
    m "Just give me a moment."
    show monika 1q
    pause 1.0

    $ monika_chr.change_hair("down")

    m 3k "And it's down!"
    m 1a "If you want my hair in a ponytail again, just ask away, [player]~"

    # lock this event, unlock hairponytail
    $ lockEventLabel("monika_hair_down")
    $ unlockEventLabel("monika_hair_ponytail")

##### End monika hair topics

## calendar-related pool event
# DEPENDS ON CALENDAR

# did we already change start date?
default persistent._mas_changed_start_date = False

# did you imply that you arent dating monika?
default persistent._mas_just_friends = False

init 5 python:
    addEvent(
        Event(
            persistent.event_database,
            eventlabel="monika_dating_startdate",
            category=["romance", "us"],
            prompt="When did we start dating?",
            pool=True,
            unlocked=False,

            # this will be unlockable via the action
            rules={"no unlock": None},

            # we'll pool this event after 30 days
            conditional=(
                "datetime.datetime.now() - persistent.sessions[" +
                "'first_session'] >= datetime.timedelta(days=30) " +
                "and persistent._mas_first_calendar_check"
            ),

            action=EV_ACT_UNLOCK
        )
    )

label monika_dating_startdate:
    $ import store.mas_calendar as mas_cal
    python:
        # we might need the raw datetime
        first_sesh_raw = persistent.sessions.get(
            "first_session",
            datetime.datetime(2017, 10, 25)
        )

        # but this to get the display plus diff
        first_sesh, _diff = mas_cal.genFriendlyDispDate(first_sesh_raw)

    if _diff.days == 0:
        # its today?!
        # this should NEVER HAPPEN
        m 1lsc "We started dating..."
        m 1wud "We started dating{fast} today?!"
        m 2wfw "You couldn't have possibly triggered this event today, [player]."
        menu:
            m "I know you're messing around with the code."
            "I'm not!":
                pass
            "You got me.":
                pass
        m 2tku "Hmph,{w} you can't fool me."

        # wait 30 days
        $ mas_chgCalEVul(30)
        return

    # Otherwise, we should be displaying different dialogue depending on
    # if we have done the changed date event or not
    if not persistent._mas_changed_start_date:
        m 1lsc "Hmmm..."
        m "I think it was..."
        m 1eua "I think it was{fast} [first_sesh]."
        m 1rksdlb "But my memory might be off."

        # ask user if correct start date
        show monika 1ekd
        menu:
            m "Is [first_sesh] correct?"
            "Yes.":
                m 1hua "Yay!{w} I remembered it."

            "No.":
                m 1rkc "Oh,{w} sorry [player]."
                m 1ekc "In that case,{w} when did we start dating?"

                call monika_dating_startdate_confirm(first_sesh_raw)

                if _return == "NOPE":
                    # we are not selecting a date today
                    return

                # save the new date to persistent
                $ store.mas_anni.reset_annis(_return)
                $ persistent.sessions["first_session"] = _return
                $ renpy.persistent.save()

        m 1eua "If you ever forget, don't be afraid to ask me."
        m 1hua "I'll {i}always{/i} remember when I first fell in love~"
        $ persistent._mas_changed_start_date = True

    else:
        m 1dsc "Let me check..."
        m 1eua "We started dating [first_sesh]."

    # TODO:
    # some dialogue about being together for x time
    # NOTE: this is a maybe

    return

label monika_dating_startdate_confirm(first_sesh_raw):

    python:
        import store.mas_calendar as mas_cal

        # and this is the formal version of the datetime
        first_sesh_formal = " ".join([
            first_sesh_raw.strftime("%B"),
            mas_cal._formatDay(first_sesh_raw.day) + ",",
            str(first_sesh_raw.year)
        ])

        # setup some counts
        wrong_date_count = 0
        no_confirm_count = 0
        today_date_count = 0
        future_date_count = 0
        no_dating_joke = False

    label .loopstart:
        pass

    call mas_start_calendar_select_date

    $ selected_date = _return
    $ _today = datetime.date.today()
    $ _ddlc_release = datetime.date(2017,9,22)

    if not selected_date or selected_date.date() == first_sesh_raw.date():
        # no date selected, we assume user wanted to cancel
        m 2dsc "[player]..."
        m 2eka "I thought you said I was wrong."
        menu:
            m "Are you sure it's not [first_sesh_formal]?"
            "It's not that date.":
                if wrong_date_count >= 2:
                    label .had_enough:
                        # monika has had enough of your shit
                        m 2dsc "..."
                        m 2lfc "We'll do this another time, then."

                        # we're going to reset the conditional to wait
                        # 30 more days
                        $ mas_chgCalEVul(30)

                        return "NOPE"

                # otherwise try again
                m 2dsc "..."
                m 2tfc "Then pick the correct date!"
                $ wrong_date_count += 1
                jump .loopstart

            "Actually that's the correct date. Sorry.":
                m 2eka "That's okay."
                $ selected_date = first_sesh_raw

    elif selected_date.date() < _ddlc_release:
        # today was chosen
        if wrong_date_count >= 2:
            jump .had_enough

        m 2dsc "..."
        m 2tfc "We did {b}not{/b} start dating that day."
        m "Take this seriously, [player]."
        $ wrong_date_count += 1
        jump .loopstart

    elif selected_date.date() == _today:
        # today was chosen
        if wrong_date_count >= 2:
            jump .had_enough

        m 2dsc "..."
        m 2tfc "We did {b}not{/b} just start dating today."
        m "Take this seriously, [player]."
        $ wrong_date_count += 1
        jump .loopstart

    elif selected_date.date() > _today:
        # you selected a future date?! why!
        if future_date_count > 0:
            # don't play around here
            jump .had_enough

        $ future_date_count += 1
        m 1wud "What..."
        menu:
            m "We haven't been dating this whole time?"
            "That was a misclick!":
                # relif expression
                m 1duu "{cps=*2}Oh, thank god.{/cps}"

                label .misclick:
                    m 2tfc "[player]!"
                    m 2eua "You had me worried there."
                    m "Don't misclick this time!"
                    jump .loopstart

            "Nope.":
                m 1dsc "..."

                show screen mas_background_timed_jump(5, "monika_dating_startdate_confirm.tooslow")

                menu:
                    "I'm kidding.":
                        hide screen mas_background_timed_jump
                        # wow what a mean joke

                        if no_dating_joke:
                            # you only get this once per thru
                            jump .had_enough

                        # otherwise mention that this was mean
                        m 2tfc "[player]!"
                        m 2rksdlc "That joke was a little mean."
                        m 2eksdlc "You really had me worried there."
                        m "Don't play around like that, okay?"
                        jump .loopstart

                    "...":
                        label .tooslow:
                            hide screen mas_background_timed_jump

                # lol why would you stay slient?
                $ persistent._mas_just_friends = True

                m 6lktdc "I see..."
                m 6dsc "..."
                m 1eka "In that case..."
                m 1tku "{cps=*4}I've got some work to do.{/cps}{nw}"

                menu:
                    "What?":
                        pass

                m 1hua "Nothing!"

                # lock this event forever probably
                # (UNTIL you rekindle or actually ask her out someday)
                $ evhand.event_database["monika_dating_startdate"].unlocked = False
                return "NOPE"

    # post loop
    python:
        new_first_sesh, _diff = mas_cal.genFriendlyDispDate(
            selected_date
        )

    m 1eua "Alright, [player]."
    m "Just to double-check..."
    menu:
        m "We started dating [new_first_sesh]."
        "Yes.":
            show monika 1eka

            # one more confirmation
            # WE WILL NOT FIX anyone's dates after this
            menu:
                m "Are you sure? I'm never going to forget this date."
                "Yes, I'm sure!":
                    m 1hua "Then it's settled!"
                    return selected_date

                "Actually...":
                    if no_confirm_count >= 2:
                        jump .notwell

                    m 1lksdlb "Aha, I figured you weren't so sure."
                    m 1eka "Try again~"
                    $ no_confirm_count += 1

        "No.":
            if no_confirm_count >= 2:
                label .notwell:
                    # are you not feeling well or something?
                    m 1eka "Are you feeling okay, [player]?"
                    m "If you don't remember right now, then we can do this again tomorrow, okay?"

                    # reset the conditional to tomorrow
                    $ mas_chgCalEVul(1)

                    return "NOPE"

            # otherwise try again
            m 1eka "Oh, that's wrong?"
            m "Then try again, [player]."
            $ no_confirm_count += 1

    # default action is to loop here
    jump .loopstart
