# ----------------------------------------------------------------------------
# Copyright (C) 2021-2022 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""Module of model error analysis check."""
from typing import Callable, Dict, Tuple, Union
from sklearn import preprocessing

from deepchecks.core import CheckResult, ConditionResult, ConditionCategory
from deepchecks.tabular import Context, TrainTestCheck, Dataset
from deepchecks.utils.metrics import ModelType
from deepchecks.utils.performance.error_model import model_error_contribution, error_model_display
from deepchecks.utils.single_sample_metrics import per_sample_cross_entropy, per_sample_mse
from deepchecks.utils.strings import format_percent


__all__ = ['ModelErrorAnalysis']


class ModelErrorAnalysis(TrainTestCheck):
    """Find features that best split the data into segments of high and low model error.

    The check trains a regression model to predict the error of the user's model. Then, the features scoring the highest
    feature importance for the error regression model are selected and the distribution of the error vs the feature
    values is plotted. The check results are shown only if the error regression model manages to predict the error
    well enough.

    Parameters
    ----------
    max_features_to_show : int , default: 3
        maximal number of features to show error distribution for.
    min_feature_contribution : float , default: 0.15
        minimum feature importance of a feature to the error regression model
        in order to show the feature.
    min_error_model_score : float , default: 0.5
        minimum r^2 score of the error regression model for displaying the check.
    min_segment_size : float , default: 0.05
        minimal fraction of data that can comprise a weak segment.
    alternative_scorer : Tuple[str, Callable] , default None
        An optional dictionary of scorer name to scorer function. Only a single entry is allowed in this check.
        If none given, using default scorer
    n_samples : int , default: 50_000
        number of samples to use for this check.
    n_display_samples : int , default: 5_000
        number of samples to display in scatter plot.
    random_state : int, default: 42
        random seed for all check internals.

    Notes
    -----
    Scorers are a convention of sklearn to evaluate a model.
    `See scorers documentation <https://scikit-learn.org/stable/modules/model_evaluation.html#scoring>`_
    A scorer is a function which accepts (model, X, y_true) and returns a float result which is the score.
    For every scorer higher scores are better than lower scores.

    You can create a scorer out of existing sklearn metrics:

    .. code-block:: python

        from sklearn.metrics import roc_auc_score, make_scorer
        auc_scorer = make_scorer(roc_auc_score)

    Or you can implement your own:

    .. code-block:: python

        from sklearn.metrics import make_scorer


        def my_mse(y_true, y_pred):
            return (y_true - y_pred) ** 2


        # Mark greater_is_better=False, since scorers always suppose to return
        # value to maximize.
        my_mse_scorer = make_scorer(my_mse, greater_is_better=False)
    """

    def __init__(
            self,
            max_features_to_show: int = 3,
            min_feature_contribution: float = 0.15,
            min_error_model_score: float = 0.5,
            min_segment_size: float = 0.05,
            alternative_scorer: Tuple[str, Union[str, Callable]] = None,
            n_samples: int = 50_000,
            n_display_samples: int = 5_000,
            random_state: int = 42,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.max_features_to_show = max_features_to_show
        self.min_feature_contribution = min_feature_contribution
        self.min_error_model_score = min_error_model_score
        self.min_segment_size = min_segment_size
        self.user_scorer = dict([alternative_scorer]) if alternative_scorer else None
        self.n_samples = n_samples
        self.n_display_samples = n_display_samples
        self.random_state = random_state

    def run_logic(self, context: Context) -> CheckResult:
        """Run check."""
        train_dataset = context.train
        test_dataset = context.test
        train_dataset.assert_label()
        task_type = context.task_type
        model = context.model

        scorer = context.get_single_scorer(self.user_scorer)
        train_dataset = train_dataset.sample(self.n_samples, random_state=self.random_state, drop_na_label=True)
        test_dataset = test_dataset.sample(self.n_samples, random_state=self.random_state, drop_na_label=True)

        # Create scoring function, used to calculate the per sample model error
        if task_type == ModelType.REGRESSION:
            def scoring_func(dataset: Dataset):
                return per_sample_mse(dataset.label_col, model.predict(dataset.features_columns))
        else:
            le = preprocessing.LabelEncoder()
            le.fit(train_dataset.classes)

            def scoring_func(dataset: Dataset):
                encoded_label = le.transform(dataset.label_col)
                return per_sample_cross_entropy(encoded_label,
                                                model.predict_proba(dataset.features_columns))

        train_scores = scoring_func(train_dataset)
        test_scores = scoring_func(test_dataset)

        cat_features = train_dataset.cat_features
        numeric_features = [num_feature for num_feature in train_dataset.features if num_feature not in cat_features]

        error_fi, error_model_predicted = model_error_contribution(train_dataset.features_columns,
                                                                   train_scores,
                                                                   test_dataset.features_columns,
                                                                   test_scores,
                                                                   numeric_features,
                                                                   cat_features,
                                                                   min_error_model_score=self.min_error_model_score,
                                                                   random_state=self.random_state)

        display, value = error_model_display(error_fi,
                                             error_model_predicted,
                                             test_dataset,
                                             model,
                                             scorer,
                                             self.max_features_to_show,
                                             self.min_feature_contribution,
                                             self.n_display_samples,
                                             self.min_segment_size,
                                             self.random_state)

        headnote = """<span>
            The following graphs show the distribution of error for top features that are most useful for distinguishing
            high error samples from low error samples.
        </span>"""
        display = [headnote] + display if display else None

        return CheckResult(value, display=display)

    def add_condition_segments_performance_relative_difference_not_greater_than(self, max_ratio_change: float = 0.05):
        """Add condition - require that the difference of performance between the segments does not exceed a ratio.

        Parameters
        ----------
        max_ratio_change : float , default: 0.05
            maximal ratio of change between the two segments' performance.
        """

        def condition(result: Dict) -> ConditionResult:
            fails = {}
            feature_res = result['feature_segments']
            for feature in feature_res.keys():
                # If only one segment identified, skip
                if len(feature_res[feature]) < 2:
                    continue
                performance_diff = (
                    abs(feature_res[feature]['segment1']['score'] - feature_res[feature]['segment2']['score']) /
                    abs(max(feature_res[feature]['segment1']['score'], feature_res[feature]['segment2']['score'])))
                if performance_diff > max_ratio_change:
                    fails[feature] = format_percent(performance_diff)

            if fails:
                sorted_fails = dict(sorted(fails.items(), key=lambda item: item[1]))
                msg = f'Found change in {result["scorer_name"]} in features above threshold: {sorted_fails}'
                return ConditionResult(ConditionCategory.WARN, msg)
            else:
                return ConditionResult(ConditionCategory.PASS)

        return self.add_condition(f'The performance difference of the detected segments must'
                                  f' not be greater than {format_percent(max_ratio_change)}', condition)
