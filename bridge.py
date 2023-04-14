'''
Things yet to do: 
	double, redouble

	allow opponents to bid 

	interpret other partner bids

	save time by treating equivalent cards in one go

	getting opener's rebid currently only works for 1m - 1M
'''

import numpy as np
import random
from termcolor import colored
import os
import time
from itertools import combinations

PLAYER_NAMES = ["North", "East", "South", "West"]
SUITS = ["Clubs", "Diamonds", "Hearts", "Spades"]
VALUES = ["Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Jack", "Queen", "King", "Ace"]
BID_SUITS = ["C", "D", "H", "S", "N"]
SUIT_SYMBOLS = [u'\u2663', u'\u2666', u'\u2665', u'\u2660']

PART_SCORE_BONUS = 50
GAME_BONUS = [300, 500]
SMALL_SLAM_BONUS = [500, 750]
GRAND_SLAM_BONUS = [1000, 1500]
UNDERTRICKS = [50, 100]

BALANCED_HANDS = [[3,3,3,4], [2,3,4,4], [2,3,3,5]]


def get_valid_moves(hand, previous):
	if previous == []:
		return sorted(hand.cards, key = lambda card: card.value)[::-1]
	else:
		suit_led = previous[0].suit 
		following_suit = hand.cards_by_suit[suit_led]
		if following_suit == []:
			return sorted(hand.cards, key = lambda card: card.value)
		elif len(previous) == 1:
			return sorted(following_suit, key = lambda card: card.value)
		else:
			return sorted(following_suit, key = lambda card: card.value)[::-1]

def get_best_card_index(cards, trump_suit):
	trump_cards = [card for card in cards if card.suit == trump_suit]
	trump_cards = sorted(trump_cards, key = lambda card: card.value)
	following_suit = [card for card in cards if card.suit == cards[0].suit]
	following_suit = sorted(following_suit, key = lambda card: card.value)
	if trump_cards != []:
		best_card = trump_cards[-1]
	else:
		best_card = following_suit[-1]
	return cards.index(best_card)

def get_suit_order(trump_suit):
	if trump_suit == 0:
		return [0,2,3,1]
	elif trump_suit == 1:
		return [1,3,2,0]
	elif trump_suit == 2:
		return [2,3,1,0]
	else:
		return [3,2,0,1]
		
def get_score(contract, trick_count, vul):
	score = 0
	if trick_count >= contract.level + 6:
		trick_count -= 6
		if contract.suit in [0,1]:
			score += 20 * trick_count
			if contract.level < 5:
				score += PART_SCORE_BONUS
			if contract.level >= 5:
				score += GAME_BONUS[vul]
			if contract.level >= 6:
				score += SMALL_SLAM_BONUS[vul]
			if contract.level >= 7:
				score += GRAND_SLAM_BONUS[vul]
		elif contract.suit in [2,3]:
			score += 30 * trick_count
			if contract.level < 4:
				score += PART_SCORE_BONUS
			if contract.level >= 4:
				score += GAME_BONUS[vul]
			if contract.level >= 6:
				score += SMALL_SLAM_BONUS[vul]
			if contract.level >= 7:
				score += GRAND_SLAM_BONUS[vul]
		elif contract.suit == 4:
			score += 10
			score += 30 * trick_count
			if contract.level < 3:
				score += PART_SCORE_BONUS
			if contract.level >= 3:
				score += GAME_BONUS[vul]
			if contract.level >= 6:
				score += SMALL_SLAM_BONUS[vul]
			if contract.level >= 7:
				score += GRAND_SLAM_BONUS[vul]
	else:
		under = contract.level + 6 - trick_count
		score -= UNDERTRICKS[vul] * under
	return score

def get_opening_bid(player, partner_passed):
	bid_to_make = 'P'
	
	'''
	# very strong hand -- bid 2C
	if player.hand.hcp >= 22:
		bid_to_make = '2C'
		player.hand.update_classification("game-going")
		player.update_hcp(22, 40)
	'''

	# player has an opening hand
	if player.hand.hcp >= 12:

		# check for balanced distribution before making NT bids
		if (player.hand.is_balanced()) and (player.hand.hcp >= 15) and (player.hand.hcp <= 17):
				bid_to_make = '1N'
		elif (player.hand.is_balanced()) and (player.hand.hcp >= 20) and (player.hand.hcp <= 21):
				bid_to_make = '2N'

		# make a 1M or 1m bid
		else:
			# check for a 5 card major
			if player.hand.lengths[3] >= 5:
				bid_to_make = '1S'
			elif player.hand.lengths[2] >= 5:
				bid_to_make = '1H'
			else:
				# bid a minor
				if player.hand.lengths[0] == player.hand.lengths[1]:
					# with three diamonds and clubs each, open 1C
					if player.hand.lengths[0] == 3:
						bid_to_make = '1C' 
					# otherwise open 1D
					else:
						bid_to_make = '1D'
				else:
					# bid the longer minor
					if player.hand.lengths[0] < player.hand.lengths[1]:
						bid_to_make = '1D'
					else:
						bid_to_make = '1C'

	'''
	# otherwise preempt if a weak hand with a long suit, subject to 5 <= hcp <= 10
	elif (max(player.hand.lengths) >= 6) and (player.hand.hcp >= 5) and (player.hand.hcp <= 10):
		suit_to_bid = np.argmax(player.hand.lengths)
		# only preempt if the suit is decent, i.e. at least 4 points in the suit
		if player.hand.suit_hcp[suit_to_bid] >= max([4, player.hand.hcp / 2]):
			level_to_bid = max(player.hand.lengths) - 4
			# 2C bid is not a preempt
			if (suit_to_bid == 0) and (level_to_bid == 2):
				# turn this bid into a pass
				level_to_bid = 0
			bid_to_make = Bid(level_to_bid, suit_to_bid).abbr

		# if >=4 card major and partner hasn't had a chance to open yet, do not preempt
		if ((player.hand.lengths[2] >= 4) or (player.hand.lengths[3] >= 4)) and (not partner_passed):
			bid_to_make = 'P'
	'''

	# return the bid abbreviation, along with instructions for partner's next bid
	return (bid_to_make, "responder 1")


def interpret_opening_bid(opening_bid):
	interpretation = [(0,40), (0,40), [(0,13), (0,13), (0,13), (0,13)]]
	fit_suit = 4

	# 1 level bids, either suit or NT
	if opening_bid.level == 1:
		
		# NT bids
		if opening_bid.suit == 4:
			interpretation = [(15,17), (15,40), [(2,5), (2,5), (2,5), (2,5)]]

		# minor suit bid
		elif opening_bid.suit in [0,1]:
			interpretation[0] = (12,19)
			interpretation[1] = (12,40)
			for i in range(4):
				if i == opening_bid.suit:
					interpretation[2][i] = (3,12)
				elif i in [0,1]:
					interpretation[2][i] = (0,6)
				else:
					interpretation[2][i] = (0,4)

		# major suit bid
		else:
			interpretation[0] = (12,19)
			interpretation[1] = (12,40)
			for i in range(4):
				if i == opening_bid.suit:
					interpretation[2][i] = (5,12)
				elif i in [2,3]:
					interpretation[2][i] = (0,6)
				else:
					interpretation[2][i] = (0,8)

	elif opening_bid.level == 2:

		# NT bids
		if opening_bid.suit == 4:
			interpretation = [(20,21), (20,40), [(2,5), (2,5), (2,5), (2,5)]]

		# stuff for 2 club opener

		# stuff for preempts

	# stuff for 3 level preempts

	return (interpretation, fit_suit)


def interpret_overcall(auction, opener):
	# opponents will always pass for now
	interpretation = [(0,40), (0,40), [(0,13), (0,13), (0,13), (0,13)]]
	fit_suit = 4

	opening_bid = auction.bid_history[opener]
	overcall_bid = auction.bid_history[opener + 1]

	return (interpretation, fit_suit)


# partner has opened the auction, overcaller has passed, get next bid
def get_responding_bid(player, prev_partner_bid, overcalled = False):
	bid_to_make = 'P'
	forcing = False

	# what are the best suits other than partner's?
	other_lengths = list(player.hand.lengths)
	suits_by_length = []
	for i in range(4):
		suits_by_length.append(np.argmax(other_lengths))
		other_lengths[np.argmax(other_lengths)] = 0
	candidate_suits = []
	for suit in suits_by_length:
		if (suit != prev_partner_bid.suit) and (player.hand.lengths[suit] >= 4) and ((player.hand.suit_hcp[suit] >= 4) or (player.hand.lengths[suit] >= 5)):
			candidate_suits.append(suit)

	req_next_bid = None

	# don't respond with under 6 hcp
	if player.hand.hcp >= 6:

		# partner bid 1 of a minor
		if (prev_partner_bid.suit in [0,1]) and (prev_partner_bid.level == 1):

			# with a four card major, bid it instead
			if player.hand.lengths[2] >= 7:
				bid_to_make = '1H'
			elif player.hand.lengths[3] >= 7:
				bid_to_make = '1S'
			elif player.hand.lengths[2] >= 6:
				bid_to_make = '1H'
			elif player.hand.lengths[3] >= 6:
				bid_to_make = '1S'
			elif player.hand.lengths[2] >= 5:
				bid_to_make = '1H'
			elif player.hand.lengths[3] >= 5:
				bid_to_make = '1S'
			elif player.hand.lengths[2] >= 4:
				bid_to_make = '1H'
			elif player.hand.lengths[3] >= 4:
				bid_to_make = '1S'

			# no four card major, see if there is support for partner's minor, factoring in distributional points
			elif player.hand.lengths[prev_partner_bid.suit] >= 5:
				pts = player.hand.hcp 
				for length in player.hand.lengths:
					if length <= 2:
						pts += 5 - 2*length
				if pts <= 10:
					bid_to_make = Bid(2, prev_partner_bid.suit).abbr
				else:
					bid_to_make = Bid(3, prev_partner_bid.suit).abbr

			# bid the other minor with five of them
			elif (player.hand.lengths[1] >= 5) and (prev_partner_bid.suit == 0):
				bid_to_make = "1D"
			elif (player.hand.lengths[0] >= 5) and (prev_partner_bid.suit == 1) and (player.hand.hcp >= 10):
				bid_to_make = "2C"

			# if none of the above fit, bid some NT to show point count
			elif player.hand.hcp <= 9:
				bid_to_make = '1N'
			elif player.hand.hcp <= 12:
				bid_to_make = '2N'
			elif player.hand.hcp <= 15:
				bid_to_make = '3N'

		# partner bid 1 of a major
		elif (prev_partner_bid.suit in [2,3]) and (prev_partner_bid.level == 1):

			# with support, let partner know
			if player.hand.lengths[prev_partner_bid.suit] >= 3:
				pts = player.hand.hcp 
				for length in player.hand.lengths:
					if length <= 2:
						pts += 5 - 2*length
				if pts <= 10:
					bid_to_make = Bid(2, prev_partner_bid.suit).abbr
				elif pts <= 12:
					bid_to_make = Bid(3, prev_partner_bid.suit).abbr
				else:
					# with at least four card support, make a Jacoby 2NT bid
					if player.hand.lengths[prev_partner_bid.suit] >= 4:
						bid_to_make = "2N"
					else:
						bid_to_make = Bid(4, prev_partner_bid.suit).abbr

			# can raise 1H to 1S with 4 spades and no heart support
			elif (prev_partner_bid.suit == 2) and (player.hand.lengths[3] >= 4):
				bid_to_make = "1S"

			# if there is a strong suit other than partner's, bid it at 2 level
			elif (player.hand.hcp >= 10) and (candidate_suits != []):
				bid_to_make	= Bid(2, candidate_suits[0]).abbr

			# if not in the above cases, there's no major fit and no strong second suit
			else:
				bid_to_make = "1N"

	# bid to make is forcing if it is a new suit, not NT
	if bid_to_make != 'P':
		if (bid_to_make[1] != prev_partner_bid.abbr[1]) and (bid_to_make[1] != prev_partner_bid.abbr[1]):
			forcing = True

	return (bid_to_make, "opener 2", forcing, req_next_bid)


def interpret_response(auction, opener):
	interpretation = [(0,40), (0,40), [(0,13), (0,13), (0,13), (0,13)]]
	fit_suit = 4

	opening_bid = auction.bid_history[opener]
	resp_bid = auction.bid_history[opener + 2]

	# opening 1 of a minor
	if (opening_bid.suit in [0,1]) and (opening_bid.level == 1):
		
		# responding 1 of a major
		if (resp_bid.suit in [2,3]) and (resp_bid.level == 1):
			interpretation[0] = (6,40)
			interpretation[1] = (6,40)
			for i in range(4):
				if i == resp_bid.suit:
					interpretation[2][i] = (4,13)
				elif i in [2,3]:
					interpretation[2][i] = (0,6)
				else: 
					interpretation[2][i] = (0,9)

		# raising partner's minor
		elif resp_bid.suit == opening_bid.suit:
			for i in range(4): 
				if i == resp_bid.suit:
					interpretation[2][i] = (5,13)
				else:
					interpretation[2][i] = (0,8)
			if resp_bid.level == 2:
				interpretation[0] = (0,10)
				interpretation[1] = (6,10)
			elif resp_bid.level == 3:
				interpretation[0] = (1,12)
				interpretation[1] = (11,40)

		# bidding the other minor
		elif resp_bid.suit in [0,1]:
			for i in range(4):
				if i == resp_bid.suit:
					interpretation[2][i] = (5,13)
				elif i in [0,1]:
					interpretation[2][i] = (0,4)
				else:
					interpretation[2][i] = (0,3)
			if resp_bid.level == 1:
				interpretation[0] = (6,40)
				interpretation[1] = (6,40)
			elif resp_bid.level == 2:
				interpretation[0] = (10,40)
				interpretation[1] = (10,40)

		# bidding no trump
		elif resp_bid.suit == 4:
			if resp_bid.level == 1:
				interpretation[0] = (6,10)
				interpretation[1] = (6,10)
				for i in range(4):
					if i == opening_bid.suit:
						interpretation[2][i] = (0,4)
					elif i in [0,1]:
						interpretation[2][i] = (3,12)
					else: 
						interpretation[2][i] = (0,3)
			else:
				for i in range(4):
					if i == opening_bid.suit:
						interpretation[2][i] = (3,4)
					elif i in [0,1]:
						interpretation[2][i] = (3,4)
					else:
						interpretation[2][i] = (2,3)
				if resp_bid.level == 2:
					interpretation[0] = (10,12)
					interpretation[1] = (10,12)
				elif resp_bid.level == 3:
					interpretation[0] = (13,40)
					interpretation[1] = (13,40)

	# opening 1 of a major 
	elif (opening_bid.suit in [2,3]) and (opening_bid.level == 1):

		# responding in the same suit
		if resp_bid.suit == opening_bid.suit:
			fit_suit = opening_bid.suit
			for i in range(4):
				if i == resp_bid.suit:
					interpretation[2][i] = (3,13)
				else:
					interpretation[2][i] = (0,10)
			if resp_bid.level == 2:
				interpretation[0] = (0,10)
				interpretation[1] = (6,10)
			elif resp_bid.level == 3:
				interpretation[0] = (1,12)
				interpretation[1] = (11,12)
			elif resp_bid.level == 4:
				interpretation[0] = (3,40)
				interpretation[1] = (13,40)

		# responding with a Jacoby 2NT bid
		elif (resp_bid.suit == 4) and (resp_bid.level == 2):
			for i in range(4):
				if i == opening_bid.suit:
					interpretation[2][i] = (4,13)
				else:
					interpretation[2][i] = (0,9)
			interpretation[0] = (3,40)
			interpretation[1] = (13,40)
			fit_suit = opening_bid.suit

		# raising 1H -> 1S
		elif (opening_bid.abbr == '1H') and (resp_bid.abbr == '1S'):
			interpretation[0] = (6,40)
			interpretation[1] = (6,40)
			for i in range(2):
				interpretation[2][i] = (0,9)
			interpretation[2][2] = (0,2)
			interpretation[2][3] = (4,13)

		# bidding a new suit at 2 level
		elif (resp_bid.suit != opening_bid.suit) and (resp_bid.level == 2):
			interpretation[0] = (10,40)
			interpretation[1] = (10,40)
			for i in range(4):
				if i == resp_bid.suit:
					interpretation[2][i] = (4,13)
				elif i == opening_bid.suit:
					interpretation[2][i] = (0,2)
				else:
					interpretation[2][i] = (0,6)

		# responding with 1NT
		elif (resp_bid.suit == 4) and (resp_bid.level == 1):
			interpretation[0] = (6,10)
			interpretation[1] = (6,10)
			for i in range(4):
				if i == opening_bid.suit:
					interpretation[2][i] = (0,2)
				elif (i == 3) and (opening_bid.suit == 2):
					interpretation[2][i] = (0,3)
				else: 
					interpretation[2][i] = (0,11)
			'''
			else:
				for i in range(4):
					if i == opening_bid.suit:
						interpretation[2][i] = (1,2)
					else:
						interpretation[2][i] = (3,4)
				if resp_bid.level == 2:
					interpretation[0] = (10,12)
					interpretation[1] = (10,12)
				elif resp_bid.level == 3:
					interpretation[0] = (13,40)
					interpretation[1] = (13,40)
			'''

	if resp_bid.level == 0:
		interpretation = [(0,5), (0,40), [(0,13), (0,13), (0,13), (0,13)]]

	return (interpretation, fit_suit)


def get_opener_rebid(player, opening_bid, resp_bid, auction):
	legal_bids = auction.possible_bids
	bid_to_make = 'P'

	# arrange suits by length
	other_lengths = list(player.hand.lengths)
	suits_by_length = []
	for i in range(4):
		suits_by_length.append(np.argmax(other_lengths))
		other_lengths[np.argmax(other_lengths)] = 0
	print(suits_by_length)

	# see if there is a suit for which a reverse is possible
	reverse_suits = []
	biddable_reverses = []
	for suit in suits_by_length:
		if (opening_bid.suit < suit) and (suit < resp_bid.suit):
			reverse_suits.append(suit)
			if player.hand.lengths[suit] >= 4:
				biddable_reverses.append(suit)
	print(reverse_suits)
	print(biddable_reverses)

	candidate_non_reverses = []
	for suit in suits_by_length:
		if (suit not in reverse_suits) and (player.hand.lengths[suit] >= 4) and (suit not in [opening_bid.suit, resp_bid.suit]):
			candidate_non_reverses.append(suit)
	print(candidate_non_reverses)

	candidates = []
	for suit in suits_by_length:
		if (suit not in [opening_bid.suit, resp_bid.suit]) and (player.hand.lengths[suit] >= 4):
			candidates.append(suit)

	# opening 1 of a minor
	if (opening_bid.suit in [0,1]) and (opening_bid.level == 1):

		# responding 1 of a minor (1C - 1D)
		if (resp_bid.suit in [0,1]) and (resp_bid.level == 1):

			# bid a major with four of them, hearts first
			if player.hand.lengths[2] >= 4:
				bid_to_make = "1H"
			elif player.hand.lengths[3] >= 4:
				bid_to_make = "1S"

			# see if there is support for partner's minor (they have >= 5D)
			elif player.hand.lengths[1] >= 3:
				pts = player.hand.hcp
				for length in player.hand.lengths:
					if length <= 2:
						pts += 3 - length
				if pts <= 16:
					bid_to_make = Bid(2, resp_bid.suit).abbr
				else:
					bid_to_make = Bid(3, resp_bid.suit).abbr

			# minimum rebids
			elif player.hand.hcp <= 16:
				if player.hand.is_balanced():
					bid_to_make = "1N"
				elif player.hand.lengths[opening_bid.suit] >= 5:
					bid_to_make = Bid(2, opening_bid.suit).abbr 

			# invitational rebids
			elif player.hand.hcp <= 18:
				if player.hand.is_balanced():
					bid_to_make = "2N"
				else:
					bid_to_make = Bid(3, opening_bid.suit).abbr

			else:
				bid_to_make = "3N"

		# responding 1 of a major
		elif (resp_bid.suit in [2,3]) and (resp_bid.level == 1):

			# with support, let partner know
			if player.hand.lengths[resp_bid.suit] >= 4:
				pts = player.hand.hcp 
				for length in player.hand.lengths:
					if length <= 2:
						pts += 3 - length
				if pts <= 16:
					bid_to_make = Bid(2, resp_bid.suit).abbr
				elif pts <= 18:
					bid_to_make = Bid(3, resp_bid.suit).abbr
				else:
					bid_to_make = Bid(4, resp_bid.suit).abbr

			# bidding 1S over 1H
			elif (resp_bid.suit == 2) and player.hand.lengths[3] >= 4:
				bid_to_make = "1S"

			# minimum rebids
			elif player.hand.hcp <= 16:
				if candidate_non_reverses != []:
					bid_to_make = Bid(2, candidate_non_reverses[0]).abbr
				elif player.hand.is_balanced():
					bid_to_make = "1N"
				elif player.hand.lengths[opening_bid.suit] >= 5:
					bid_to_make = Bid(2, opening_bid.suit).abbr

			# invitational rebids
			elif player.hand.hcp <= 18:
				if candidates != []:
					bid_to_make = Bid(2, candidates[0]).abbr 
				elif player.hand.is_balanced():
					bid_to_make = "2N"
				else:
					bid_to_make = Bid(3, opening_bid.suit).abbr

			# game-forcing rebids
			else:
				# make a jump-shift if possible
				if candidates != []:
					bid_to_make = Bid(3, candidates[0]).abbr 
				else:
					bid_to_make = "3N"

		# responding 1NT
		elif (resp_bid.suit == 4) and (resp_bid.level == 1):
			pass


	print(bid_to_make)
	return bid_to_make


def update_interpretations(interpretation, new_information, player_index):

	fit_suit = new_information[1]
	new_information = new_information[0]

	for i in range(2):
		interpretation[i][player_index] = (max(interpretation[i][player_index][0], new_information[i][0]), min(interpretation[i][player_index][1], new_information[i][1]))

	for i in range(4):
		interpretation[2][player_index][i] = (max(interpretation[2][player_index][i][0], new_information[2][i][0]), min(interpretation[2][player_index][i][1], new_information[2][i][1]))

	return interpretation, fit_suit


def interpret_auction(auction):
	shown_hcp = [(0,40), (0,40), (0,40), (0,40)]
	shown_points = [(0,40), (0,40), (0,40), (0,40)]
	shown_lengths = [[(0,13), (0,13), (0,13), (0,13)], [(0,13), (0,13), (0,13), (0,13)], [(0,13), (0,13), (0,13), (0,13)], [(0,13), (0,13), (0,13), (0,13)]]

	n_s_fit = [4]
	e_w_fit = [4]

	bid_index = 0
	passed_so_far = True
	opener = 0
	while passed_so_far:
		if auction.bid_history[bid_index].abbr == 'P':
			shown_hcp[(bid_index + auction.dealer) % 4] = (0,11)
		else:
			opener = bid_index
			passed_so_far = False
			(shown_hcp, shown_points, shown_lengths), fit_suit = update_interpretations((shown_hcp, shown_points, shown_lengths), interpret_opening_bid(auction.bid_history[bid_index]), (bid_index + auction.dealer) % 4)
			if (bid_index + auction.dealer) % 2 == 0:
				n_s_fit.append(fit_suit)
			else:
				e_w_fit.append(fit_suit)
		bid_index += 1

	# next player to bid is the overcaller, interpret their bid (PASS for now)
	(shown_hcp, shown_points, shown_lengths), fit_suit = update_interpretations((shown_hcp, shown_points, shown_lengths), interpret_overcall(auction, opener), (bid_index + auction.dealer) % 4)
	if (bid_index + auction.dealer) % 2 == 0:
		n_s_fit.append(fit_suit)
	else:
		e_w_fit.append(fit_suit)
	bid_index += 1

	# next player to bid is the responder, interpret their bid
	(shown_hcp, shown_points, shown_lengths), fit_suit = update_interpretations((shown_hcp, shown_points, shown_lengths), interpret_response(auction, opener), (bid_index + auction.dealer) % 4)
	if (bid_index + auction.dealer) % 2 == 0:
		n_s_fit.append(fit_suit)
	else:
		e_w_fit.append(fit_suit)
	bid_index += 1

	# update max values, if one player has e.g. 3 hearts, new max is 10 hearts 
	for suit_index in range(4):
		shown_instances = 0
		for i in range(4):
			shown_instances += shown_lengths[i][suit_index][0]
		for i in range(4):
			new_most = 13 - (shown_instances - shown_lengths[i][suit_index][0])
			shown_lengths[i][suit_index] = (shown_lengths[i][suit_index][0], min([new_most, shown_lengths[i][suit_index][1]]))

	# perform the same update for hcp
	collective_hcp = 0
	for i in range(4):
		collective_hcp += shown_hcp[i][0]
	for i in range(4):
		new_most = 40 - (collective_hcp - shown_hcp[i][0])
		shown_hcp[i] = (shown_hcp[i][0], min([new_most, shown_hcp[i][1]]))

	''' OLD WAY OF CHECKING FITS
	# check for north/south fit
	for north_bid in [bid for bid in [bidd for bidd in auction.bid_table[0]if bidd != ''] if bid.level != 0]:
		if n_s_fit != 4:
			break
		for south_bid in [bid for bid in [bidd for bidd in auction.bid_table[2]if bidd != ''] if bid.level != 0]:
			if north_bid.suit == south_bid.suit:
				n_s_fit = [north_bid.suit, auction.n_s_first_bidders[north_bid.suit]]
				break

	# check for east/west fit
	for east_bid in [bid for bid in [bidd for bidd in auction.bid_table[1]if bidd != ''] if bid.level != 0]:
		if e_w_fit != 4:
			break
		for west_bid in [bid for bid in [bidd for bidd in auction.bid_table[3]if bidd != ''] if bid.level != 0]:
			if east_bid.suit == west_bid.suit:
				e_w_fit = [east_bid.suit, auction.e_w_first_bidders[east_bid.suit]]
				break
	'''

	# make sure there's only one copy of each "suit" in the fit lists
	n_s_fit = list(set(n_s_fit))
	e_w_fit = list(set(e_w_fit))

	return (shown_hcp, shown_points, shown_lengths, n_s_fit, e_w_fit)


def matches_auction(hand_pair, player_indices, interpretation):
	shown_hcp, shown_points, shown_lengths, n_s_fit, e_w_fit = interpretation
	for i in range(2):
		hand = Hand(hand_pair[i])
		player = player_indices[i]
		if (hand.hcp < shown_hcp[player][0]) or (hand.hcp > shown_hcp[player][1]):
			return False
		if player in [0,2]:
			if len(n_s_fit) == 2:
				if n_s_fit[1] == player:
					ind = 0
				else:
					ind = 1
				if (hand.hcp + hand.dist_pts[n_s_fit[0]][ind] < shown_points[player][0]) or (hand.hcp + hand.dist_pts[n_s_fit[0]][ind] > shown_points[player][1]):
					return False
		elif player in [1,3]:
			if len(e_w_fit) == 2:
				if e_w_fit[1] == player:
					ind = 0
				else:
					ind = 1
				if (hand.hcp + hand.dist_pts[e_w_fit[0]][ind] < shown_points[player][0]) or (hand.hcp + hand.dist_pts[e_w_fit[0]][ind] > shown_points[player][1]):
					return False
		for suit_index in range(4):
			if (hand.lengths[suit_index] < shown_lengths[player][suit_index][0]) or (hand.lengths[suit_index] > shown_lengths[player][suit_index][1]):
				return False
	return True


def get_best_move(player, models, table, model_candidates, sample_size, depth = 13):

	good_team = player.index % 2

	sample_size = min(sample_size, len(model_candidates))

	initial_count = [0 for i in range(len(player.hand.cards))]
	random.shuffle(model_candidates)

	first_unknown = 0
	second_unknown = 0

	best_cards = []
	for k in range(sample_size):
		for i in range(4):
			if models[i] == None:
				first_unknown = i
				models[i] = Hand(list(set(model_candidates[k][0]) - set(table.cards_played[i])))
				for j in range(4):
					if models[j] == None:
						second_unknown = j
						models[j] = Hand(list(set(model_candidates[k][1]) - set(table.cards_played[j])))

		#cards_left_for_trick = (table.starting_player - player.index) % 4
		previously_played = table.cards_on_table
		global best_card
		start_player = player.index
		start_hand_length = len(models[player.index].cards)

		valid_moves = get_valid_moves(models[player.index], previously_played)
		best_card = valid_moves[0]

		depth = min(depth, start_hand_length)


		def recursive_moves(player, models, table, previously_played, depth, alpha = -1, beta = 14):

			global best_card

			if depth == 0:
				return (models[start_player].hcp + models[(start_player + 2) % 2].hcp) / 40

			max_score = -1
			min_score = 14

			for card in get_valid_moves(models[player.index], previously_played):
				new_prev = list(previously_played)
				new_prev.append(card)
				if len(new_prev) == 4:
					resetting = True
					winner = get_best_card_index(new_prev, table.trump_suit)
					new_prev = []
					if (winner + player.index + 1) % 2 == good_team:
						trick_bonus = 1
					else:
						trick_bonus = 0
				else:
					resetting = False
				new_models = list(models)
				new_models[player.index] = Hand([i for i in new_models[player.index].cards if i != card])
				if resetting:
					score = recursive_moves(table.players[(player.index + winner + 1) % 4], new_models, table, new_prev, depth - 1, alpha, beta) + trick_bonus
				else:
					score = recursive_moves(table.players[(player.index + 1) % 4], new_models, table, new_prev, depth, alpha, beta)
				if player.index % 2 == good_team:
					if score > max_score:
						max_score = score 
						if (len(models[player.index].cards) == start_hand_length) and (player.index == start_player):
							best_card = card
					if score >= beta:
						break;
					alpha = max(alpha, score)
				else:
					if score < min_score:
						min_score = score 
					if score <= alpha:
						break
					beta = min(beta, score)
			if player.index % 2 == good_team:
				return max_score
			else:
				return min_score

		recursive_moves(player, models, table, previously_played, depth)
		best_cards.append(best_card)
		models[first_unknown] = None
		models[second_unknown] = None

	return max(best_cards, key = best_cards.count)



		


class Card:

	def __init__(self, value, suit):
		self.value = value
		self.suit = suit

		self.name = VALUES[value] + " of " + SUITS[suit]

		self.abbr = ""
		if value <= 7:
			self.abbr += str(value + 2)
		else:
			self.abbr += VALUES[value][0]
		self.abbr += SUITS[suit][0]

		self.cabbr = self.abbr[0]
		self.cabbr += SUIT_SYMBOLS[self.suit]
		if self.suit in [1,2]:
			self.cabbr = colored(self.cabbr, "red")

		self.hcp = 0
		if value == 12:
			self.hcp = 4
		elif value == 11:
			self.hcp = 3
		elif value == 10:
			self.hcp = 2
		elif value == 9:
			self.hcp = 1


class Deck:

	def __init__(self):
		self.cards = []
		for i in range(4):
			for j in range(13):
				self.cards.append(Card(j,i))

	def shuffle(self):
		random.shuffle(self.cards)

	def draw_card(self):
		return self.cards.pop(0)

	def deal(self, players):
		for player in players:
			new_cards = [self.draw_card() for i in range(13)]
			player.hand = Hand(new_cards)


class Player:

	def __init__(self, index):
		self.index = index

		self.name = PLAYER_NAMES[self.index]

		self.hand = Hand([])

		self.card_in_play = "  "

		self.bid_list = []

		self.preferred_suit = None

		self.hcp_min = 0
		self.hcp_max = 40

		self.points_min = 0
		self.points_max = 40

		self.fit_suit = 4

	def update_bids(self, bid):
		self.bid_list.append(bid)

	def update_suit(self, suit_index):
		self.preferred_suit = suit_index

	def update_hcp(self, new_min, new_max):
		if self.hcp_min < new_min:
			self.hcp_min = new_min
		if self.hcp_max > new_max:
			self.hcp_max = new_max

	def update_pts(self, new_min, new_max):
		if self.points_min < new_min:
			self.points_min = new_min
		if self.points_max > new_max:
			self.points_max = new_max

	def reset_points(self):
		self.hcp_min = 0
		self.hcp_max = 40

		self.points_min = 0
		self.points_max = 40


class Human(Player):

	def is_human():
		return True

	def get_play(self, table):
		string_hand = [str(card.abbr) for card in self.hand.cards]
		valid_moves = get_valid_moves(self.hand, table.cards_on_table)
		valid_strings = [str(card.abbr) for card in valid_moves]
		time.sleep(.5)
		while True:
			card_to_play = input("Please enter a card to play: ").upper()
			if card_to_play in valid_strings:
				return string_hand.index(card_to_play)

	def get_bid(self, auction):
		valid_bid_strings = [str(bid.abbr) for bid in auction.possible_bids]
		while True:
			bid_to_make = input("Please enter your bid: ").upper()
			if bid_to_make in valid_bid_strings:
				return valid_bid_strings.index(bid_to_make)


class Robot(Player):

	def is_human():
		return False

	def get_play(self, table):
		moves = get_valid_moves(self.hand, table.cards_on_table)
		if len(moves) == 1:
			return self.hand.cards.index(moves[0])
		else:
			known_indices = [self.index, table.dummy]
			total_cards_seen = table.players[table.dummy].hand.cards + self.hand.cards
			for i in range(4):
				for card in table.cards_played[i]:
					total_cards_seen.append(card)
			if self.index == table.dummy:
				total_cards_seen += table.players[(table.dummy + 2) % 4].hand.cards
				known_indices.append((table.dummy + 2) % 4)
			seen_as_tuples = [(card.value, card.suit) for card in total_cards_seen]
			all_as_tuples = [(card.value, card.suit) for card in Deck().cards]
			remaining_cards_as_tuples = list(set(all_as_tuples) - set(seen_as_tuples))
			remaining_cards = [Card(tup[0], tup[1]) for tup in remaining_cards_as_tuples]

			unknown_player_indices = sorted(list(set([0,1,2,3]) - set(known_indices)))

			current_length = 13 - len(table.cards_played[unknown_player_indices[0]])
			if current_length < 11:
				candidates = [(table.cards_played[unknown_player_indices[0]] + list(combo), table.cards_played[unknown_player_indices[1]] + list(set(remaining_cards) - set(combo))) for combo in list(combinations(remaining_cards, current_length))]
				if len(candidates) > 500:
					sampled_candidates = random.sample(candidates, 500)
				else:
					sampled_candidates = candidates
			else:
				samples_drawn = [random.sample(remaining_cards, current_length) for i in range(500)]
				sampled_candidates = [(table.cards_played[unknown_player_indices[0]] + samp, list(set(remaining_cards) - set(samp))) for samp in samples_drawn]
			good_candidates = [pair for pair in sampled_candidates if matches_auction(pair, unknown_player_indices, interpret_auction(table.auction))]

			if len(good_candidates) != 0:
				Hand(good_candidates[0][0]).show()
				Hand(good_candidates[0][1]).show()
				if current_length >= 11:
					depth = 2
					samples = 15
				elif current_length >= 6:
					depth = 3
					samples = 10
				else:
					depth = 4
					samples = 10

				models = [None, None, None, None]
				for player_index in range(4):
					if player_index in known_indices:
						models[player_index] = table.players[player_index].hand
				card_to_play = get_best_move(self, models, table, good_candidates, samples, depth)

			else:
				random.shuffle(moves)
				card_to_play = moves[0]

			return self.hand.cards.index(card_to_play)

	def get_bid(self, auction):
		partner = auction.players[(self.index + 2) % 4]
		# filter out first "" placeholders
		partner_bids = list(filter(lambda key: key != "", auction.bid_table[partner.index]))
		partner_bids = list(filter(lambda key: key.abbr != "P", partner_bids))
		my_bids = list(filter(lambda key: key != "", auction.bid_table[self.index]))
		my_bids = list(filter(lambda key: key.abbr != "P", my_bids))
		partner_has_bid = True
		partner_first_bid_pass = True
		partner_always_passed = True
		if partner_bids == []:
			partner_has_bid = False
		elif partner_bids[0].abbr != 'P':
			partner_first_bid_pass = False
			partner_always_passed = False
		else:
			for bid in partner_bids:
				if bid.abbr != 'P':
					partner_always_passed = False
		valid_bid_strings = [str(bid.abbr) for bid in auction.possible_bids]
		time.sleep(.5)
		if not auction.is_opened():
			return valid_bid_strings.index(get_opening_bid(self, partner_has_bid)[0])
		elif (len(partner_bids) == 1) and (not partner_first_bid_pass) and (len(my_bids) == 0):
			return valid_bid_strings.index(get_responding_bid(self, partner_bids[0])[0])
		elif (len(partner_bids) == 1) and (len(my_bids) == 1):
			return valid_bid_strings.index(get_opener_rebid(self, my_bids[0], partner_bids[0], auction))
		else:
			return valid_bid_strings.index('P')


class Hand:

	def __init__(self, cards):
		self.cards = cards

		self.hcp = 0
		for card in self.cards:
			self.hcp += card.hcp

		self.points = self.hcp

		self.cards_by_suit = [[card for card in self.cards if card.suit == i] for i in range(4)]
		self.lengths = [len(suit) for suit in self.cards_by_suit]

		self.suit_hcp = []
		for i in range(4):
			suit_pts = 0
			for card in self.cards_by_suit[i]:
				suit_pts += card.hcp
			self.suit_hcp.append(suit_pts)

		self.classification = "unknown"

		self.dist_pts = []
		for i in range(4):
			if self.lengths[i] <= 2:
				self.dist_pts.append((3 - self.lengths[i], 5 - 2*self.lengths[i]))
			else:
				self.dist_pts.append((0,0))
		self.dist_pts.append((0,0))

	def is_balanced(self):
		lengths_to_check = sorted(self.lengths)
		if lengths_to_check in BALANCED_HANDS:
			return True
		else:
			return False

	def update_classification(self, new_classification):
		self.classification = new_classification

	def sort(self, suit_order = [3,2,0,1]):
		new_cards = []
		for index in suit_order:
			suit_cards = sorted(self.cards_by_suit[index], key = lambda card: card.value)
			suit_cards.reverse()
			new_cards += suit_cards
		self.cards = new_cards

	def show(self):
		self.sort()
		print(*[card.cabbr for card in self.cards])


class Table:

	def __init__(self, auction, contract, declarer, running_score):
		self.players = auction.players
		self.deck = auction.deck
		self.auction = auction
		self.contract = contract
		self.declarer = declarer
		self.running_score = running_score
		self.starting_player = (self.declarer + 1) % 4
		self.dummy = (self.starting_player + 1) % 4
		self.cards_played = [[],[],[],[]]

		if self.declarer in [0,2]:
			declarer_hand = self.players[self.declarer].hand
			self.players[self.declarer] = Human(self.declarer)
			self.players[self.declarer].hand = declarer_hand

			dummy_hand = self.players[self.dummy].hand
			self.players[self.dummy] = Human(self.dummy)
			self.players[self.dummy].hand = dummy_hand

		self.show_dummy = False
		if self.declarer == 0:
			show_dummy = True

		self.required_tricks = 6 + self.contract.level
		self.trump_suit = self.contract.suit

		self.suit_order = get_suit_order(self.trump_suit)

		for player in self.players:
			player.hand.sort(self.suit_order)

		self.cards_on_table = []

		self.n_s_trick_count = 0
		self.e_w_trick_count = 0

	def display(self):
		os.system("clear")
		print("")
		if (self.dummy == 0 or self.dummy == 2) and self.show_dummy:
			print(" "*26, *[card.cabbr for card in self.players[0].hand.cards])
		else:
			print("")
		print("")
		print(" "*26, "-"*38)
		print(" "*25, "|", " "*36, "|")
		for index in range(4):
			if (self.dummy == 3) and self.show_dummy:
				west_cards = sorted(self.players[3].hand.cards_by_suit[self.suit_order[index]], key = lambda card: card.value)
				west_cards.reverse()
				east_cards = []
			elif (self.dummy == 1) and self.show_dummy:
				east_cards = sorted(self.players[1].hand.cards_by_suit[self.suit_order[index]], key = lambda card: card.value)
				east_cards.reverse()
				west_cards = []
			else:
				west_cards = []
				east_cards = []
			west_slot = ["  ", self.players[3].card_in_play, "  ", "  "]
			north_south_slot = [self.players[0].card_in_play, "  ", "  ", self.players[2].card_in_play]
			east_slot = ["  ", self.players[1].card_in_play, "  ", "  "]
			print(*[card.cabbr for card in west_cards], " "*(26 - 3*len(west_cards) - 1), "|", " "*16, north_south_slot[index], " "*16, "|", " "*(26 - 3*len(east_cards) - 1), *[card.cabbr for card in east_cards])
			print(" "*25, "|", " "*3, west_slot[index], "  "*11, east_slot[index], " "*3, "|")
		print(" "*26, "-"*38)
		print("")
		print(" "*26, *[card.cabbr for card in self.players[2].hand.cards])
		score_string = str(self.n_s_trick_count) + " : " + str(self.e_w_trick_count)
		print("Running score:", self.running_score, " "*(70 - len(str(self.running_score))), "NS", " "*(len(score_string) - 5) + "EW")
		if self.dummy in [1,3]:
			print("Contract:", self.contract.cabbr, "by", self.players[self.declarer].name, " "*65, self.n_s_trick_count, ":", self.e_w_trick_count)
		elif self.dummy in [0,2]:
			print("Contract:", self.contract.cabbr, "by", self.players[self.declarer].name, " "*64, self.n_s_trick_count, ":", self.e_w_trick_count)
		print("")

	def play_trick(self, starting_player):
		self.display()
		player_order = [(starting_player + i) % 4 for i in range(4)]
		for index in player_order:
			card_index = self.players[index].get_play(self)
			choice = self.players[index].hand.cards.pop(card_index)
			self.players[index].card_in_play = choice.cabbr
			self.players[index].hand = Hand(self.players[index].hand.cards)
			self.cards_on_table.append(choice)
			self.show_dummy = True
			self.display()
			self.cards_played[index].append(choice)
		winner = player_order[get_best_card_index(self.cards_on_table, self.trump_suit)]
		if winner in [0,2]:
			self.n_s_trick_count += 1 
		else:
			self.e_w_trick_count += 1
		self.starting_player = winner
		self.cards_on_table = []
		for player in self.players:
			player.card_in_play = "  "
		input("")
		self.display()


class Auction:
	
	def __init__(self, players, deck, dealer, n_s_vul, e_w_vul):
		self.players = players
		self.deck = deck
		self.dealer = dealer
		self.n_s_vul = n_s_vul
		self.e_w_vul = e_w_vul

		self.deck.shuffle()
		self.deck.deal(self.players)

		# for bid debugging
		for player in self.players:
			print(player.name)
			player.hand.show()

		self.n_s_first_bidders = ['','','','','']
		self.e_w_first_bidders = ['','','','','']

		self.final_bid = Bid(0,0)
		self.declarer = dealer

		self.bid_table = [[], [], [], []]

		for player in self.players:
			player.reset_points()
			player.hand.sort()
			if player.index < self.dealer:
				self.bid_table[player.index].append("")

		self.possible_bids = []
		for i in range(7):
			for j in range(5):
				self.possible_bids.append(Bid(i+1,j))
		self.possible_bids.append(Bid(0,0))

		self.bid_history = []

	def is_competitive(self):
		if (self.n_s_first_bidders != ['','','','','']) or (self.e_w_first_bidders != ['','','','','']):
			return False
		else:
			return True

	def display(self):
		if self.n_s_vul:
			north_symbol = colored("N", "red")
			south_symbol = colored("S", "red")
		else:
			north_symbol = "N"
			south_symbol = "S"
		if self.e_w_vul:
			east_symbol = colored("E", "red")
			west_symbol = colored("W", "red")
		else:
			east_symbol = "E"
			west_symbol = "W"
		spacing = 7
		os.system("clear")
		print("")
		print(" "*26, "-"*38)
		print(" "*25, "|", " "*36, "|")
		print(" "*25, "|  ", north_symbol, " "*spacing, east_symbol, " "*spacing, south_symbol, " "*spacing, west_symbol, "   |")
		error_count = 0
		depth = 0
		while error_count < 4:
			error_count = 0
			bidding_round = ""
			for i in range(4):
				try:
					bid = self.bid_table[i][depth]
					if bid == "":
						bidding_round += " "*(spacing + 3)
					else:
						bidding_round += bid.cabbr
						if i < 3:
							bidding_round += " "*(spacing + 1)
				except IndexError:
					error_count += 1
					if i < 3:
						bidding_round += " "*(spacing + 3)
					if i == 3:
						bidding_round += "  "
			depth += 1
			print(" "*25, "|  ", bidding_round, "  |")
		print(" "*26, "-"*38)
		print("")
		print(" "*26, *[card.cabbr for card in self.players[2].hand.cards])
		print("")
		
	def is_over(self):
		if len(self.possible_bids) <= 1:
			return True
		elif [bid.abbr for bid in self.bid_history[-3:]] == [Bid(0,0).abbr for i in range(3)]:
			if len(self.bid_history) > 3:
				return True
		else:
			return False

	def is_opened(self):
		for bid in self.bid_history:
			if bid.abbr != 'P':
				return True
		return False

	def make_bid(self, player):
		bid_index = player.get_bid(self)

		# second condition temporary to stop opponents bidding
		if (bid_index != len(self.possible_bids) - 1) and (player.index in [0,2]):
			bid = self.possible_bids.pop(bid_index)
			self.possible_bids = self.possible_bids[bid_index:]
			if player.index in [0,2]:
				if self.n_s_first_bidders[bid.suit] == '':
					self.n_s_first_bidders[bid.suit] = player.index
			elif player.index in [1,3]:
				if self.e_w_first_bidders[bid.suit] == '':
					self.e_w_first_bidders[bid.suit] = player.index
		else:
			bid = Bid(0,0)
		self.bid_history.append(bid)
		self.bid_table[player.index].append(bid)
		self.display()


class Bid:

	def __init__(self, level, suit):
		self.suit = suit
		self.level = level

		self.abbr = str(self.level) + str(BID_SUITS[suit])
		if self.level == 0:
			self.abbr = "P"

		self.cabbr = self.abbr
		if self.suit in [1,2]:
			self.cabbr = colored(self.abbr, "red")
		elif self.suit == 4:
			self.cabbr = colored(self.abbr, "blue")
		elif self.level == 0:
			self.cabbr = colored(self.abbr + " ", "green")


def play_loop(players):
	done_playing = False
	dealer = 0
	running_score = 0
	board_count = 1
	n_s_vul = False
	e_w_vul = False
	while not done_playing:
		players[0] = Robot(0)
		score = play_board(players, dealer, n_s_vul, e_w_vul, running_score)
		running_score += score 
		if score != 0:
			print("Score:", score)
		play_again = input("Would you like to play another board? ").lower()
		if play_again.startswith('y'):
			if (board_count % 3) == 0:
				n_s_vul = True
				e_w_vul = True
			elif (board_count % 3) == 1:
				n_s_vul = True
				e_w_vul = False
			elif (board_count % 3) == 2:
				n_s_vul = False
				e_w_vul = True
			board_count += 1
			dealer = (dealer + 1) % 4
		else:
			done_playing = True



def play_board(players, dealer, n_s_vul, e_w_vul, running_score):
	deck = Deck()
	auction = Auction(players, deck, dealer, n_s_vul, e_w_vul)
	auction.display()

	finished = False
	passed_out = False
	player_to_bid = dealer
	while not finished:
		auction.make_bid(players[player_to_bid])
		if [bid.abbr for bid in auction.bid_history] == ['P' for i in range(4)]:
			finished = True
			passed_out = True
		elif auction.is_over():
			for player in players:
				player.hand.show()
			print(interpret_auction(auction))
			finished = True
			if auction.bid_history[-1].abbr == '7N':
				contract = Bid(7,4)
				if player_to_bid in [0,2]:
					declarer = auction.n_s_first_bidders[contract.suit]
				elif player_to_bid in [1,3]:
					declarer = auction.e_w_first_bidders[contract.suit]
			else: 
				contract = auction.bid_history[-4]
				if player_to_bid in [1,3]:
					declarer = auction.n_s_first_bidders[contract.suit]
				elif player_to_bid in [0,2]:
					declarer = auction.e_w_first_bidders[contract.suit]
		else:
			player_to_bid = (player_to_bid + 1) % 4
	if not passed_out:
		return play_hand(auction, contract, declarer, running_score)
	else:
		return 0


def play_hand(auction, contract, declarer, running_score):
	table = Table(auction, contract, declarer, running_score)

	play = input("Would you like to play the hand? ").lower()
	if play.startswith('y'):
		table.display()

		for i in range(13): 
			table.play_trick(table.starting_player)

		if declarer in [0,2]:
			return get_score(contract, table.n_s_trick_count, auction.n_s_vul)
		elif declarer in [1,3]:
			return -1 * get_score(contract, table.e_w_trick_count, auction.e_w_vul)
	else:
		return 0


play_loop([Robot(0), Robot(1), Human(2), Robot(3)])

'''
auction = Auction([Robot(0), Robot(1), Robot(2), Robot(3)], Deck(), 0, False, False)
table = Table(auction, Bid(1,2), 2, 0)
models = [[Card(12,2), Card(10,0), Card(4,2)], [Card(6,3), Card(11, 2), Card(11,0)], [Card(7,2), Card(9,0), Card(12,1)], [Card(8,0), Card(1,2), Card(1,3)]]
models = [Hand(model) for model in models]
print(get_best_move(auction.players[0], models, table, [], 1).cabbr)
'''



