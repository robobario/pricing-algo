#!/usr/bin/env python

import unittest

TRANSPARENCY = "transparency"
DSP = "dsp"
AGENCY = "agency"
COUNTRY = "country"
ADFORMAT = "adformat"


def specificity(product):
    return len(product["product_features"])


class Model:
    def __init__(self, _model):
        self.model = _model
        self.tiers = {}
        for name, product in model["products"].items():
            tier = specificity(product)
            if tier in self.tiers:
                self.tiers[tier].append(product)
            else:
                self.tiers[tier] = [product]

    def get_tier(self, key):
        return self.tiers[key]

    def get_segment(self, segment_id):
        return self.model["buyer-segments"][segment_id]

    def get_buyer(self, buyer_id):
        return self.model["buyers"][buyer_id]


class Algorithm:
    def __init__(self, model_dict):
        self.model = Model(model_dict)

    def get_price(self, product_features, buyer_features):
        # rules are organised into tiers by specificity, the more product features the higher the tier
        tiers = reversed(sorted(self.model.tiers.keys()))
        for tier in tiers:  # iterate from high specificity to low
            price = self.highest_matching_price_in_tier(tier, product_features, buyer_features)
            if price is not None:
                print("found price in tier [{}] : {} stop the search!".format(tier, price))
                return price
            else:
                print("found no matching rules with specificity " + str(tier))
        return None

    def highest_matching_price_in_tier(self, tier, product_features, buyer_features):
        products = self.model.get_tier(tier)
        highest_price = None
        for product in products:
            price = self.highest_matching_price_in_product(product, product_features, buyer_features)
            if price is not None and (highest_price is None or price > highest_price):
                print("- found new highest price [{}], greater than [{}] within tier {}".format(price, highest_price, tier))
                highest_price = price
        return highest_price

    def highest_matching_price_in_product(self, product, product_features, buyer_features):
        if not self.product_matches(product, product_features):
            return None
        print("--- found a rule with product-features [{}] matching impression [{}] ".format(product["product_features"], product_features))
        highest_price = None
        highest_spec = None
        for offer in product["offers"]:
            offer_spec = self.offer_matches(offer, buyer_features, product_features)
            price = offer["price"]
            higher_spec = offer_spec is not None and (highest_spec is None or offer_spec > highest_spec)
            higher_price = price is not None and (highest_price is None or price > highest_price)
            if higher_spec or (higher_price and offer_spec == highest_spec):
                highest_spec = offer_spec
                print("---- found an offer with a matching buyer {}".format(str(offer)))
                print("---- found a price {} higher than the last max {}".format(str(price), str(highest_price)))
                highest_price = price
        print("--- highest price found : {}".format(highest_price))
        return highest_price

    def offer_matches(self, offer, buyer_features, product_features):
        if not self.feature_matches_eq(offer, product_features, TRANSPARENCY):
            print(
                "---- offer transparency {} did not match impression transparency {}".format(str(offer[TRANSPARENCY]),
                                                                                             str(product_features[TRANSPARENCY])))
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
        "rule2": {
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


if __name__ == '__main__':
    unittest.main()
