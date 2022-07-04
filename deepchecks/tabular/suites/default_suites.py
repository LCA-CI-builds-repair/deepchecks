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
"""Functions for loading the default (built-in) suites for various validation stages.

Each function returns a new suite that is initialized with a list of checks and default conditions.
It is possible to customize these suites by editing the checks and conditions inside it after the suites' creation.
"""
import warnings

from deepchecks.tabular import Suite
from deepchecks.tabular.checks import (BoostingOverfit, CalibrationScore, CategoryMismatchTrainTest, ConflictingLabels,
                                       ConfusionMatrixReport, DataDuplicates, DatasetsSizeComparison,
                                       DateTrainTestLeakageDuplicates, DateTrainTestLeakageOverlap,
                                       FeatureLabelCorrelation, FeatureLabelCorrelationChange,
                                       IdentifierLabelCorrelation, IndexTrainTestLeakage, IsSingleValue, MixedDataTypes,
                                       MixedNulls, ModelInferenceTime, NewLabelTrainTest, OutlierSampleDetection,
                                       PerformanceReport, RegressionErrorDistribution, RegressionSystematicError,
                                       RocReport, SimpleModelComparison, SpecialCharacters,
                                       StringLengthOutOfBounds, StringMismatch, StringMismatchComparison,
                                       TrainTestFeatureDrift, TrainTestLabelDrift, TrainTestPredictionDrift,
                                       TrainTestSamplesMix, UnusedFeatures, WeakSegmentsPerformance, WholeDatasetDrift)

__all__ = ['single_dataset_integrity', 'train_test_leakage', 'train_test_validation',
           'model_evaluation', 'full_suite']


def single_dataset_integrity(**kwargs) -> Suite:
    """
    Create a suite that is meant to detect integrity issues within a single dataset (Deprecated).

    .. deprecated:: 0.7.0
            `single_dataset_integrity` is deprecated and will be removed in deepchecks 0.8 version, it is replaced by
            `data_integrity` suite.
    """
    warnings.warn(
        'the single_dataset_integrity suite is deprecated, use the data_integrity suite instead',
        DeprecationWarning
    )
    return data_integrity(**kwargs)


def data_integrity(**kwargs) -> Suite:
    """Create a suite that is meant to detect integrity issues within a single dataset."""
    return Suite(
        'Data Integrity Suite',
        IsSingleValue(**kwargs).add_condition_not_single_value(),
        SpecialCharacters(**kwargs).add_condition_ratio_of_special_characters_less_or_equal(),
        MixedNulls(**kwargs).add_condition_different_nulls_less_equal_to(),
        MixedDataTypes(**kwargs).add_condition_rare_type_ratio_not_in_range(),
        StringMismatch(**kwargs).add_condition_no_variants(),
        DataDuplicates(**kwargs).add_condition_ratio_less_or_equal(),
        StringLengthOutOfBounds(**kwargs).add_condition_ratio_of_outliers_less_or_equal(),
        ConflictingLabels(**kwargs).add_condition_ratio_of_conflicting_labels_less_or_equal(),
        OutlierSampleDetection(**kwargs),
        FeatureLabelCorrelation(**kwargs).add_condition_feature_pps_less_than(),
        IdentifierLabelCorrelation(**kwargs).add_condition_pps_less_or_equal()
    )


def train_test_leakage(**kwargs) -> Suite:
    """
    Create a suite that is meant to detect data leakage between the training dataset and the test dataset (Deprecated).

    .. deprecated:: 0.7.0
        `train_test_leakage` is deprecated and will be removed in deepchecks 0.8 version, it is replaced by
        `train_test_validation` suite.
    """
    warnings.warn(
        'the train_test_leakage suite is deprecated, use the train_test_validation suite instead',
        DeprecationWarning
    )
    return train_test_validation(**kwargs)


def train_test_validation(**kwargs) -> Suite:
    """Create a suite that is meant to validate correctness of train-test split, including integrity, \
    distribution and leakage checks."""
    return Suite(
        'Train Test Validation Suite',
        DatasetsSizeComparison(**kwargs).add_condition_test_train_size_ratio_greater_than(),
        NewLabelTrainTest(**kwargs).add_condition_new_labels_number_less_or_equal(),
        CategoryMismatchTrainTest(**kwargs).add_condition_new_category_ratio_less_or_equal(),
        StringMismatchComparison(**kwargs).add_condition_no_new_variants(),
        DateTrainTestLeakageDuplicates(**kwargs).add_condition_leakage_ratio_less_or_equal(),
        DateTrainTestLeakageOverlap(**kwargs).add_condition_leakage_ratio_less_or_equal(),
        IndexTrainTestLeakage(**kwargs).add_condition_ratio_less_or_equal(),
        TrainTestSamplesMix(**kwargs).add_condition_duplicates_ratio_less_or_equal(),
        FeatureLabelCorrelationChange(**kwargs).add_condition_feature_pps_difference_less_than()
        .add_condition_feature_pps_in_train_less_than(),
        TrainTestFeatureDrift(**kwargs).add_condition_drift_score_less_than(),
        TrainTestLabelDrift(**kwargs).add_condition_drift_score_less_than(),
        WholeDatasetDrift(**kwargs).add_condition_overall_drift_value_less_than(),
    )


def model_evaluation(**kwargs) -> Suite:
    """Create a suite that is meant to test model performance and overfit."""
    return Suite(
        'Model Evaluation Suite',
        PerformanceReport(**kwargs).add_condition_train_test_relative_degradation_not_greater_than(),
        RocReport(**kwargs).add_condition_auc_greater_than(),
        ConfusionMatrixReport(**kwargs),
        TrainTestPredictionDrift(**kwargs).add_condition_drift_score_less_than(),
        SimpleModelComparison(**kwargs).add_condition_gain_greater_than(),
        WeakSegmentsPerformance(**kwargs).add_condition_segments_relative_performance_greater_than(),
        CalibrationScore(**kwargs),
        RegressionSystematicError(**kwargs).add_condition_systematic_error_ratio_to_rmse_less_than(),
        RegressionErrorDistribution(**kwargs).add_condition_kurtosis_greater_than(),
        UnusedFeatures(**kwargs).add_condition_number_of_high_variance_unused_features_less_or_equal(),
        BoostingOverfit(**kwargs).add_condition_test_score_percent_decline_less_than(),
        ModelInferenceTime(**kwargs).add_condition_inference_time_less_than(),
    )


def full_suite(**kwargs) -> Suite:
    """Create a suite that includes many of the implemented checks, for a quick overview of your model and data."""
    return Suite(
        'Full Suite',
        model_evaluation(**kwargs),
        train_test_validation(**kwargs),
        data_integrity(**kwargs),
    )
