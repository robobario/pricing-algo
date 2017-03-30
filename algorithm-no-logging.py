#!/usr/bin/env python

import unittest

TRANSPARENCY = "transparency"
DSP = "dsp"
AGENCY = "agency"
COUNTRY = "country"
ADFORMAT = "adformat"
from collections import namedtuple
from operator import attrgetter

def specificity(product):
    return len(product["product_features"])

Tier = namedtuple("Tier", ["priority", "num_features"])

class Model:
    def __init__(self, _model):
        self.model = _model
        self.tiers = []
        products = model["products"].values()
        keyed = [(Tier(product['priority'], specificity(product)), product) for product in products]
        tiers = {}
        for (tier, product) in keyed:
            if tier in tiers:
                tiers[tier].append(product)
            else:
                tiers[tier] = [product]
        tier_keys = reversed(sorted(tiers.keys(), key=attrgetter('priority', 'num_features')))
        for key in tier_keys:
            self.tiers.append(tiers[key])

    def get_segment(self, segment_id):
        return self.model["buyer-segments"][segment_id]

    def get_buyer(self, buyer_id):
        return self.model["buyers"][buyer_id]


class Algorithm:
    def __init__(self, model_dict):
        self.model = Model(model_dict)

    def get_price(self, product_features, buyer_features):
        # rules are organised into tiers by specificity, the more product features the higher the tier
        tiers = self.model.tiers
        for tier in tiers:  # iterate from high specificity to low
            price = self.highest_matching_price_in_tier(tier, product_features, buyer_features)
            if price is not None:
                return price
        return None

    def highest_matching_price_in_tier(self, tier, product_features, buyer_features):
        products = tier
        highest_price = None
        for product in products:
            price = self.highest_matching_price_in_product(product, product_features, buyer_features)
            if price is not None and (highest_price is None or price > highest_price):
                highest_price = price
        return highest_price

    def highest_matching_price_in_product(self, product, product_features, buyer_features):
        if not self.product_matches(product, product_features):
            return None
        highest_price = None
        highest_spec = None
        for offer in product["offers"]:
            offer_spec = self.offer_matches(offer, buyer_features, product_features)
            price = offer["price"]
            higher_spec = offer_spec is not None and (highest_spec is None or offer_spec > highest_spec)
            higher_price = price is not None and (highest_price is None or price > highest_price)
            if higher_spec or (higher_price and offer_spec == highest_spec):
                highest_spec = offer_spec
                highest_price = price
        return highest_price

    def offer_matches(self, offer, buyer_features, product_features):
        if not self.feature_matches_eq(offer, product_features, TRANSPARENCY):
            return False
        buyer_groups = [self.model.get_segment(segment) for segment in offer["buyer-segments"]]
        highest_spec = None
        for group in buyer_groups:
            for buyer_id in group:
                buyer = self.model.get_buyer(buyer_id)
                spec = self.buyer_matches(buyer, buyer_features)
                if spec is not None and (highest_spec is None or spec > highest_spec):
                    highest_spec = spec
        return highest_spec

    def product_matches(self, product, product_features):
        feature_filter = product["product_features"]
        return self.features_match_filter(feature_filter, product_features)

    def buyer_matches(self, feature_filter, buyer_features):
        feature_filter = feature_filter
        match_filter = self.features_match_filter(feature_filter, buyer_features)
        if match_filter:
            return len(feature_filter)
        else:
            return None

    def features_match_filter(self, feature_filter, actual_features):
        matches = True
        for feature in feature_filter:
            feature_type = feature["feature"]
            matches = matches and self.feature_matches_in(feature, actual_features, feature_type)
        return matches

    @staticmethod
    def feature_matches_in(feature, actual_features, field):
        if not field in actual_features:
            return False
        return actual_features[field] in feature["in"]

    @staticmethod
    def feature_matches_eq(feature, actual_features, field):
        if not field in actual_features:
            return False
        return actual_features[field] == feature[field]


model = {
    "buyers": {
        "Metrigo": [
            {
                "feature": DSP,
                "in": [1]
            }
        ],
        "Other": [  # is this possible, a buyer defined by multiple features?
            {
                "feature": AGENCY,
                "in": [2]
            }, {
                "feature": DSP,
                "in": [1]
            }
        ]
    },
    "buyer-segments": {
        "adwords": ["Metrigo"],
        "Other": ["Other"],
    },
    "products": {
        "rule": {
            "priority": 1,
            "product_features": [
                {
                    "feature": ADFORMAT,
                    "in": ["460x100"]
                }
            ],
            "offers": [{
                "price": 1.3,
                TRANSPARENCY: "blind",
                "buyer-segments": ["adwords"]
            }]
        },
        "rule-exception": {
            "priority": 2,
            "product_features": [
                {
                    "feature": ADFORMAT,
                    "in": ["460x100"]
                },
                {
                    "feature": COUNTRY,
                    "in": ["CZ"]
                }
            ],
            "offers": [{
                "price": 2.2,
                TRANSPARENCY: "blind",
                "buyer-segments": ["adwords"]
            }]
        },
        "rule2": {
            "priority": 1,
            "product_features": [
                {
                    "feature": ADFORMAT,
                    "in": ["460x100"]
                },
                {
                    "feature": COUNTRY,
                    "in": ["DE"]
                }
            ],
            "offers": [{
                "price": 3.4,
                TRANSPARENCY: "blind",
                "buyer-segments": ["adwords"]
            }, {
                "price": 4.4,
                TRANSPARENCY: "open",
                "buyer-segments": ["adwords"]
            },
                {
                    "price": 4.3,
                    TRANSPARENCY: "open",
                    "buyer-segments": ["Other"]
                }
            ]
        },
        "rule-3": {
            "priority": 1,
            "product_features": [
                {
                    "feature": ADFORMAT,
                    "in": ["460x100"]
                },
                {
                    "feature": COUNTRY,
                    "in": ["CZ"]
                }
            ],
            "offers": [{
                "price": 5.4,
                TRANSPARENCY: "blind",
                "buyer-segments": ["adwords"]
            }, {
                "price": 5.4,
                TRANSPARENCY: "open",
                "buyer-segments": ["adwords"]
            },
                {
                    "price": 5.3,
                    TRANSPARENCY: "open",
                    "buyer-segments": ["Other"]
                }
            ]
        }
    }
}

class TestAlgorithm(unittest.TestCase):
    def testRuleWithASingleProductFeature(self):
        product_features = {ADFORMAT: "460x100", TRANSPARENCY: "blind"}
        buyer_features = {DSP: 1}
        algo = Algorithm(model)
        price = algo.get_price(product_features, buyer_features)
        self.assertEqual(price, 1.3)

    def testMoreSpecificProductFeaturesWin(self):
        product_features = {ADFORMAT: "460x100", TRANSPARENCY: "blind", COUNTRY: "DE"}
        buyer_features = {DSP: 1}
        algo = Algorithm(model)
        price = algo.get_price(product_features, buyer_features)
        self.assertEqual(price, 3.4)

    def testTransparencyMustMatchOffer(self):
        product_features = {ADFORMAT: "460x100", TRANSPARENCY: "open", COUNTRY: "DE"}
        buyer_features = {DSP: 1}
        algo = Algorithm(model)
        price = algo.get_price(product_features, buyer_features)
        self.assertEqual(price, 4.4)

    def testBuyerWithMultipleBuyerCriteriaIsPreferred(self):
        product_features = {ADFORMAT: "460x100", TRANSPARENCY: "open", COUNTRY: "DE"}
        buyer_features = {DSP: 1, AGENCY: 2}
        algo = Algorithm(model)
        price = algo.get_price(product_features, buyer_features)
        self.assertEqual(price, 4.3)

    def testHigherPriorityRulePrefered(self):
        product_features = {ADFORMAT: "460x100", TRANSPARENCY: "open", COUNTRY: "CZ"}
        buyer_features = {DSP: 1, AGENCY: 2}
        algo = Algorithm(model)
        price = algo.get_price(product_features, buyer_features)
        self.assertEqual(price, 2.2)


if __name__ == '__main__':
    unittest.main()
