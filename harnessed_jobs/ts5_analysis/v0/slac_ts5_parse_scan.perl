#!/usr/bin/perl
use strict;
use warnings;
use POSIX;
use Statistics::Regression;
use Getopt::Long;
use File::Basename;
use List::AllUtils qw ( bsearch_index );
use Cwd;
use Astro::FITS::CFITSIO qw( :constants );

my $kframe_db=dirname($0);
my $kframe_datafile={
    ("1" => $kframe_db."/KFrame_data/KFrame1_170228/byregion.tnt",
     "2" => $kframe_db."/KFrame_data/KFrame2_170503/byregion.tnt",
     "3" => $kframe_db."/KFrame_data/KFrame3_170914/byregion.tnt",
     "4" => $kframe_db."/KFrame_data/KFrame4_171122/byregion.tnt")};

# allocate the db array object

my $db=[];
my $usage="USAGE:\t$0 [args] scanfile1 scanfile2 ..\n".
    "\t[args] are any combination of:\n\n".
    "\t--help\n".
    "\t--KFrame=<kframe_id> #(specify KFrame data file drawn from CMM data)\n".
    "\t\tkframe_id options include:\n";

foreach my $kfix (sort keys %{$kframe_datafile}) {
    $usage .= sprintf("\t\t%s for %s\n",$kfix,$kframe_datafile->{$kfix})
}

# process command lines

my $kframe_id=1;
my $help=0;

GetOptions("KFrame=s" => \$kframe_id,
	   "help"     => \$help) || 
    die("error in command line arguments! exiting..\n",$usage);

# get the filename on the commandline

my $filenames=[@ARGV];

my $str="\n";
$str .= sprintf("$0 will run with the following parameters:\n");
$str .= sprintf("\tKFrame id = %s\n",$kframe_id);
$str .= sprintf("\t\t(%s)\n",$kframe_datafile->{$kframe_id});
$str .= sprintf("\tinput files = (%s)\n",join(' ',@{$filenames}));

printf STDERR "%s\n",$str;
if ($help) {
    printf STDERR "%s\n",$usage;
    exit;
}
if (!@{$filenames}) {
    printf STDERR "nothing to do!\n%s\n",$usage;
    exit;
}

foreach my $fn_ix (0..$#{$filenames}) {
    my $cleanup=0;

    $db->[$fn_ix] = {};
    $db->[$fn_ix]->{"filename"} = $filenames->[$fn_ix];

    if (dirname($filenames->[$fn_ix]) ne ".") {
	# copy the input file to the working directory for operating on
	my $cmd=sprintf("cp %s .",$filenames->[$fn_ix]);
	`$cmd`;
	$filenames->[$fn_ix] = basename($filenames->[$fn_ix]);
	$db->[$fn_ix]->{"filename"} = $filenames->[$fn_ix];
	$cleanup=1;
    }

    if (0) {
	my $status=0;
	my $fits_filename=$filenames->[$fn_ix];
	$fits_filename =~ s/.txt$//;
	$fits_filename .= ".fits";
	unlink $fits_filename if (-e $fits_filename);
	$db->[$fn_ix]->{"fitsfile"}=
	    Astro::FITS::CFITSIO::create_file($fits_filename,$status);
    }
    
    read_scan_contents($db->[$fn_ix],{"gain"=>{"key_z1"=>cos((24.0/2.0)*atan2(1,1)/45.0),
					       "key_z2"=>cos((17.0/2.0)*atan2(1,1)/45.0)}});
#    read_scan_contents($db->[$fn_ix],{"gain"=>{"key_z1"=>cos((24.0/2.0)*atan2(1,1)/45.0),
#						   "key_z2"=>1}});

    # check for presence of a transform spec and provide "raft" coordinate system columns.
    if (defined($db->[$fn_ix]->{"TF"})) {
	my ($x0,$y0,$theta)=($db->[$fn_ix]->{"TF"}->{"X0"},
			     $db->[$fn_ix]->{"TF"}->{"Y0"},
			     $db->[$fn_ix]->{"TF"}->{"theta"});
	my ($raft_x,$raft_y)=([],[]);
	my ($sn,$cs)=(sin($theta*atan2(1,1)/45.0),cos($theta*atan2(1,1)/45.0));
	my ($xv,$yv)=($db->[$fn_ix]->{"aero_x"},$db->[$fn_ix]->{"aero_y"});
	for (my $ix=0;$ix<$db->[$fn_ix]->{"n_entry"};$ix++) {
	    $raft_x->[$ix] = +($xv->[$ix]-$x0)*$cs+($yv->[$ix]-$y0)*$sn;
	    $raft_y->[$ix] = -($xv->[$ix]-$x0)*$sn+($yv->[$ix]-$y0)*$cs;
	}
	append_column($db->[$fn_ix],"raft_x",$raft_x);
	append_column($db->[$fn_ix],"raft_y",$raft_y);
    } # if there's no transformation specs in the input file, this won't affect functionality of this code so continue.
    
    append_sum($db->[$fn_ix],["key_z1","key_z2"],"key_zsum");
    append_column($db->[$fn_ix],"I",[(1)x$db->[$fn_ix]->{"n_entry"}]);
    # maybe change split_reref_meas to also split data sets into SELFCAL sets?
    split_reref_meas($db->[$fn_ix],["_reref","_meas"],"REREF");

    # splice out the selfcal datasets.
    split_selfcal_meas($db->[$fn_ix],["_selfcal","_meas"],"SELFCAL","aero_z");
    
    populate_reref_regressions($db->[$fn_ix],"_reref",["I","aero_x","aero_y"],
			       "key_zsum","timestamp");
    populate_ref_system($db->[$fn_ix],["_reref","_meas"],"key_zsum_ref","timestamp");
    append_diff($db->[$fn_ix],["key_zsum","key_zsum_ref"],"key_zsum_ref_rr");

    if (1) {
	foreach my $dep ( "key_z1","key_z2" ) {
	    my $rgr_name = "_".$dep."_regr";
	    my $newcol_name = $dep."_rr";
	    regr_windowed_surface($db->[$fn_ix],$rgr_name,
				  ["I","aero_x","aero_y"],$dep,
				  $db->[$fn_ix]->{"_meas"},1.5);
	    remove_regression($db->[$fn_ix],$rgr_name,$newcol_name);
	}
    }

    
    # as a sanity check, output a visualization of the structure that is removed by the rereferencing step

    regr_windowed_surface($db->[$fn_ix],"_refsys_regr",
			  ["I","aero_x","aero_y"],"key_zsum_ref",
			  $db->[$fn_ix]->{"_meas"},30);
    remove_regression($db->[$fn_ix],"_refsys_regr","reref_noise");
    
    
    # make up another lateral coordinate system close to the appropriate 
    # kinematic mount support frame model. origin is as shown in marked up KFrame drawing
    if (defined($db->[$fn_ix]->{"TF"})) {
	my $tf=$db->[$fn_ix]->{"TF"};
	append_trans_coords($db->[$fn_ix],
			    ["KF_x","KF_y"],
			    {"raft_offset" => [$tf->{"X0"},$tf->{"Y0"}],
				 "theta" => $tf->{"theta"}*atan2(1,1)/45.0,
				 "MCS_offset" => [113.5/2.0-5.5,0]},
			    ["aero_x","aero_y"]);
    } else {
	# use hardcoded values from ts7-2 as a placeholder
	append_trans_coords($db->[$fn_ix],
			    ["KF_x","KF_y"],
			    {"raft_offset" => [8.25,-19.125],
				 "theta" => 0.242*atan2(1,1)/45.0,
				 "MCS_offset" => [113.5/2.0-5.5,0]},
			    ["aero_x","aero_y"]);
    }

    if (0) {
	# and add in a radial coordinate for the {"KF_x","KF_y"} system..
	my $KF_r=[];
	for (my $i=0;$i<$db->[$fn_ix]->{"n_entry"};$i++) {
	    $KF_r->[$i] = sqrt(pow($db->[$fn_ix]->{"KF_x"}->[$i]-(-(113.5/2.0-5.5)),2)+
			       pow($db->[$fn_ix]->{"KF_y"}->[$i],2));
	}
	append_column($db->[$fn_ix],"KF_r",$KF_r);
    }

    # take out any key_z1 outlier points from the set on a "label" basis because of
    # incidence of bad data on fid0
    foreach my $raw_msmt ( "key_z1","key_z2" ) {
	my $outlier_hash=regr_by_labels($db->[$fn_ix],"_".$raw_msmt."_rgr_bylabel",["I","KF_x","KF_y"],
					$raw_msmt,$db->[$fn_ix]->{"_meas"},1.5);
	pare_array($db->[$fn_ix]->{"_meas"},$outlier_hash,["fid0","fid1"],4);
    }
    
    # sample the CMM measured KMSF about 3 positions that we'll use to define a new plane
    # on the way to transfering TS5 measurements into absolute image height.
    my $cmm_BPref_file=$kframe_datafile->{$kframe_id};
    my $tmpdb={};
    $tmpdb->{"filename"}=$cmm_BPref_file;
    read_scan_contents($tmpdb);
    append_column($tmpdb,"I",[(1)x$tmpdb->{"n_entry"}]);

    my $delete_columns_later={$tmpdb => [],$db->[$fn_ix] => []};
    
    {   # append a twist term for fitting
	my $twist=[];
	foreach my $i (0..$#{$tmpdb->{"xreq"}}) {
	    $twist->[$i] = $tmpdb->{"xreq"}->[$i]*$tmpdb->{"yreq"}->[$i];
	}
	append_column($tmpdb,"xreq_by_yreq",$twist);
	push(@{$delete_columns_later->{$tmpdb}},"xreq_by_yreq");
	$twist=[];
	foreach my $i (0..$#{$db->[$fn_ix]->{"KF_x"}}) {
	    $twist->[$i] = $db->[$fn_ix]->{"KF_x"}->[$i]*$db->[$fn_ix]->{"KF_y"}->[$i];
	}
	append_column($db->[$fn_ix],"KF_x_by_KF_y",$twist);
	push(@{$delete_columns_later->{$db->[$fn_ix]}},"KF_x_by_KF_y");
    }
    
    my $modeling_directives={"orig_registration" => {"regr_name"  => "_orig_fidplane",
							 "extraction_list" => [[-138.2,20],[-138.2,-20],[34.3,0]],
							 "radial_tol" => 6,
							 "ms_set"     => $db->[$fn_ix],
							 "ms_indep"   => ["I","KF_x","KF_y"],
							 "ms_dep"     => "key_zsum_ref_rr",
							 "kmsf_set"   => $tmpdb,
							 "kmsf_indep" => ["I","xreq","yreq"],
							 "kmsf_dep"   => "zsum_ballplane_rr"},
				 "nearest_fidpos" => {"regr_name"  => "_nearest_fidplane",
							  "extraction_list" => [[-138,0],[34.3,-18],[34.3,18]],
							  "radial_tol" => 3,
							  "ms_set"     => $db->[$fn_ix],
							  "ms_indep"   => ["I","KF_x","KF_y"],
							  "ms_dep"     => "key_zsum_ref_rr",
							  "kmsf_set"   => $tmpdb,
							  "kmsf_indep" => ["I","xreq","yreq"],
							  "kmsf_dep"   => "zsum_ballplane_rr"},
				 "fit_fid_twist" => {"regr_name"  => "_twisted_fidplane",
							 "extraction_list" => [],
							 "radial_tol" => 3,
							 "ms_set"     => $db->[$fn_ix],
							 "ms_indep"   => ["I","KF_x","KF_y","KF_x_by_KF_y"],
							 "ms_dep"     => "key_zsum_ref_rr",
							 "kmsf_set"   => $tmpdb,
							 "kmsf_indep" => ["I","xreq","yreq","xreq_by_yreq"],
							 "kmsf_dep"   => "zsum_ballplane_rr"}};
    
    # populate a longer list for fit_fid_twist case.
    
    for (my $ycoord=-25;$ycoord<=25;$ycoord+=3) {
	push(@{$modeling_directives->{"fit_fid_twist"}->{"extraction_list"}},
	     [-138,$ycoord],[34,$ycoord]);
    }

    # loop over the modeling directives and perform regressions on each dataset:
    foreach my $mdkey ( keys %{$modeling_directives} ) {
	my $md=$modeling_directives->{$mdkey};
	regr_sample_rgns($md->{"kmsf_set"},$md->{"regr_name"},
			 [@{$md->{"kmsf_indep"}}[1,2]],
			 $md->{"kmsf_indep"},$md->{"kmsf_dep"},
			 $md->{"extraction_list"},$md->{"radial_tol"});
	regr_sample_rgns($md->{"ms_set"},$md->{"regr_name"},
			 [@{$md->{"ms_indep"}}[1,2]],
			 $md->{"ms_indep"},$md->{"ms_dep"},
			 $md->{"extraction_list"},$md->{"radial_tol"});
	# compute the regression differences 
	# and evaluate on the grid of tooling ball locations
	regression_difference(
	    $db->[$fn_ix],"_ballplane_rel_".$mdkey,
	    $md->{"ms_indep"},"key_zsum_ref_rr",
	    $db->[$fn_ix]->{$md->{"regr_name"}}->{"regr"}->{"theta"},
	    $tmpdb->{$md->{"regr_name"}}->{"regr"}->{"theta"});

	if ($mdkey =~ /twist/) {
	    # sample the 3 locations corresponding to the kinematic ball load paths
	    # so that we can compare twisted & untwisted models in the same breath.
	    my $ball_centers=[[-108,0],[5.55,43.27],[5.55,-43.27]];
	    my $corrected_ballplane_regr=
		Statistics::Regression->new("BALLCENTERS",
					    [@{$md->{"ms_indep"}}[0..2]]);
	    foreach my $ball (@{$ball_centers}) {
		my $theta=
		    $md->{"ms_set"}->{"_ballplane_rel_".$mdkey}->{"regr"}->{"theta"};
		my $ball_z;
		$ball_z  = $theta->[0];
		$ball_z += $theta->[1]*$ball->[0];
		$ball_z += $theta->[2]*$ball->[1];
		$ball_z += $theta->[3]*$ball->[0]*$ball->[1];
		$corrected_ballplane_regr->include($ball_z,[1,@{$ball}]);
	    }
	    # shove aside the twisted fit as a new name and reassign the
	    # corrected_balllapen_regr to be referred to by this mdkey

	    # give them a new name
	    $md->{"ms_set"}->{"_ballplane_rel_".$mdkey."_withtwistpar"}=
		$md->{"ms_set"}->{"_ballplane_rel_".$mdkey}->{"regr"};

	    # do the surgery
	    $md->{"ms_set"}->{"_ballplane_rel_".$mdkey}=
	    {"regr" => {("regr_indep_axes" => [@{$md->{"ms_indep"}}[0..2]],
			 "regr_dep_axis"   => $md->{"ms_dep"},
			 "theta"           => [$corrected_ballplane_regr->theta()])}};
	}
	# now subtract off the newly prepared regression to form a new column
	remove_regression($md->{"ms_set"},"_ballplane_rel_".$mdkey,
			  "TS5_CMM_ballplane_ref_".$mdkey);
    }

    # copy over array reference for a new column name and proceed
    append_column($db->[$fn_ix],"TS5_CMM_ballplane_ref",
		  [@{$db->[$fn_ix]->{"TS5_CMM_ballplane_ref_"."fit_fid_twist"}}]);

    # detach the original
    detach_column($db->[$fn_ix],"TS5_CMM_ballplane_ref_"."fit_fid_twist");

    # compute regression for flatness column
    regr_windowed_surface($db->[$fn_ix],
			  "_windowed_ts5_cmm_ballplane_ref",
			  ["I","KF_x","KF_y"],"TS5_CMM_ballplane_ref",
			  $db->[$fn_ix]->{"_meas"},1.5);
    
    # generate flatness column
    remove_regression($db->[$fn_ix],
		      "_windowed_ts5_cmm_ballplane_ref",
		      "TS5_CMM_ballplane_ref_rr");

    # generate piecewise regression & piecewise flatness
    regr_by_labels($db->[$fn_ix],"_rgr_bylabel",
		   ["I","KF_x","KF_y"],"TS5_CMM_ballplane_ref",
		   $db->[$fn_ix]->{"_meas"},1.5);

    # at this point there should be 3 absolute height estimates, drawn from fits to fiducial
    # samples for each dataset (ms,kmsf), named:
    # {orig_registration,nearest_fidpos,fit_fid_twist}
    # regression differences in the ms datasets named:
    # "_ballplane_rel_".{orig_registration,nearest_fidpos,fit_fid_twist,fit_fid_twist_withtwistpar}
    # and corresponding (preceding) regression subtracted columns in the datasets ms named:
    # "TS5_CMM_ballplane_ref_".{orig_registration,nearest_fidpos,fit_fid_twist}
    

    printf "finished with TS5_CMM_ballplane_ref!\n";

    describe_contents($db->[$fn_ix]);
    my $export_file=$filenames->[$fn_ix];
    $export_file =~ s/.txt$//;
    $export_file .= "__ms.txt";

#    # compute the heights relative to the fiducial transfer plane decided upon.
#    remove_regression($db->[$fn_ix],"_twisted_fidplane","fiducialsamp_rr");
#    remove_regression($tmpdb,"_twisted_fidplane","fiducialsamp_rr");

    # safe to strip out unneeded columns prior to export.
    
    foreach my $hr ( $db->[$fn_ix],$tmpdb ) {
	next if (!defined($delete_columns_later->{$hr}));
	foreach my $delcol (@{$delete_columns_later->{$hr}}) {
	    detach_column($hr,$delcol);
	}
    }

    export_file($db->[$fn_ix],$export_file,["label","I"],$db->[$fn_ix]->{"_meas"});
    export_file($tmpdb,"kmsf_temp.txt",["I"],[0..$tmpdb->{"n_entry"}-1]);

    {
	my $status=0;
	my $fits_filename=$filenames->[$fn_ix];
	$fits_filename =~ s/.txt$//;
	$fits_filename .= ".fits";
	unlink $fits_filename if (-e $fits_filename);
	$db->[$fn_ix]->{"fitsfile"}=
	    Astro::FITS::CFITSIO::create_file($fits_filename,$status);

	my $fptr=$db->[$fn_ix]->{"fitsfile"};
	printf "status=$status\n" if ($status);
	$fptr->create_img(DOUBLE_IMG,2,[0,0],$status);
	printf "status=$status\n" if ($status);
	stash_fits_version($fptr,$db->[$fn_ix],
			   {"labels"=>"all"},["I"],"SLAC::TS5 DATA");
	foreach my $label ("S00", "S01", "S02",
			   "S10", "S11", "S12",
			   "S20", "S21", "S22",
			   "fid0","fid1"       ) {
	    stash_fits_version($fptr,$db->[$fn_ix],
			       {"labels"=>[$label]},["I","label"],
			       "SLAC::TS5 DATA"." (".$label.")");
	}
	stash_regressions_fits_version($fptr,$db->[$fn_ix]);
	# finally close the fits file
	$db->[$fn_ix]->{"fitsfile"}->close_file($status);
	printf "status=$status\n" if ($status);
	
	if ($cleanup==1) {
	    unlink $db->[$fn_ix]->{"filename"};
	    $cleanup=0;
	} 
    }
    # OK, so the kmsf file has been saved as many times as the ms file has been. shouldn't depend on the ms datasets anyway.
}

sub save_regressions {
    my ($this,$output_filename)=@_;
    open(GG,">",$output_filename) || die;
    printf GG "regressions performed for file %s:\n",$this->{"filename"};
    foreach my $key (sort keys %{$this}) {
	if ((ref $this->{$key} eq ref {}) &&
	    defined($this->{$key}->{"regr"})) {
	    printf GG "\tregression named %s measured against %s:\n",$key,$this->{$key}->{"regr"}->{"regr_dep_axis"};
	    printf GG "\t\tindep: %s\n",join("\t",@{$this->{$key}->{"regr"}->{"regr_indep_axes"}});
	    printf GG "\t\tpars: %s\n",join("\t",@{$this->{$key}->{"regr"}->{"theta"}});
	} else {
	    # it's not a hash or the hash doesn't contain member "regr"
	}
    }
    # now look for special key called "_reref"
    if (defined($this->{"_reref"}) && (ref $this->{"_reref"} eq ref [])) {
	printf GG "rereferencing performed:\n";
	foreach my $entry (@{$this->{"_reref"}}) {
	    if (defined($entry->{"regr"})) {
		my $st=$entry->{"regr"}->{"sort_term"};
		printf GG "! for %s : %s\n",$st,join("\t",@{$entry->{"regr"}->{"regr_indep_axes"}});
		printf GG "%s %s\n",$entry->{"regr"}->{$st},join("\t",@{$entry->{"regr"}->{"theta"}});
	    }
	}
    }
    close(GG);
}

sub remove_regression {
    my ($this,$regr,$newcolname)=@_;
    my $newcol=[];

    my $indep_axes=$this->{$regr}->{"regr"}->{"regr_indep_axes"};

    for (my $i=0;$i<$this->{"n_entry"};$i++) {
	my $regr_value=0;
	foreach my $col_ix (0..$#{$indep_axes}) {
	    my $col=$indep_axes->[$col_ix];
	    $regr_value += ($this->{$regr}->{"regr"}->{"theta"}->[$col_ix] *
			    $this->{$col}->[$i]);
	}
	$newcol->[$i] = $this->{$this->{$regr}->{"regr"}->{"regr_dep_axis"}}->[$i] - $regr_value;
    }
    append_column($this,$newcolname,$newcol);
}

sub regr_by_labels {
    # modified to return a hash of arrrays indicating outlier status (measured in sigma).
    # keys of hash are *labels*, indexes of per-label arrays are according to 
    # $starting_ix_list..
    my ($this,$new_regr_root,$regr_indep_axes,$regr_dep_axis,$starting_ix_list,$thresh_rms)=@_;
    #	    ($db->[$fn_ix],"_rgr_bylabel",["I","KF_x","KF_y"],"TS5_CMM_ballplane_ref",$db->[$fn_ix]->{"_meas"},1.5);

    if (!defined($this)) {
	printf STDERR "entry $this doesn't exist.\nexiting..\n";
	exit(1);	}
    if (!defined($this->{$regr_dep_axis})) {
	printf STDERR "dependent axis $regr_dep_axis not defined in $this.\nexiting..\n";
	exit(1);	}
    foreach my $ia (@{$regr_indep_axes}) {
	if (!defined($this->{$ia})) {
	    printf STDERR "independent axis $ia not defined in $this.\nexiting..\n";
	    exit(1);	    }	}
    # go through the list, generate regressions as needed
    my $ix_list=[@{$starting_ix_list}];
    my $iter=0;
    my $nrej=0;
    my $last_nrej=0;
    my $rms={};
    my $rgrs={};
    my $stable_rejection;
    do {
	$nrej=0;
	my $rgressn={};
	my %labs=();
	foreach my $ix (@{$ix_list}) {
	    my ($data,$model)=(0,0);
	    my $lab=$this->{"label"}->[$ix];
	    $labs{$lab}=1;
	    my $new_rgr=$new_regr_root."_".$lab;
	    if (!defined($this->{$new_rgr})) {
		$this->{$new_rgr}={};
		$this->{$new_rgr}->{"regr"}={};
		my $rgr=$this->{$new_rgr}->{"regr"};
		$rgr->{"regr_indep_axes"}=$regr_indep_axes;
		$rgr->{"regr_dep_axis"}=$regr_dep_axis;
		$rgrs->{$lab}=$rgr;
	    }
	    if (!defined($rgressn->{$lab})) {
		$rgressn->{$lab}=Statistics::Regression->new($regr_dep_axis,
							     $regr_indep_axes);
	    }
	    my $rgr=$rgrs->{$lab};
	    if ($iter!=0) {
		($data,$model)=($this->{$rgr->{"regr_dep_axis"}}->[$ix],0);
		foreach my $ia_ix (0..$#{$rgr->{"regr_indep_axes"}}) {
		    my $ia_val=$this->{$rgr->{"regr_indep_axes"}->[$ia_ix]}->[$ix];
		    my $rgr_coeff=$rgr->{"theta"}->[$ia_ix];
		    $model += $ia_val*$rgr_coeff;
		}
	    }
	    if (($iter==0)||(sqrt(pow(($data-$model)/$rms->{$lab},2))<$thresh_rms)) {
		my $datlist=[];
		foreach my $ia (@{$rgr->{"regr_indep_axes"}}) {
		    push(@{$datlist},$this->{$ia}->[$ix]);
		}
		$rgressn->{$lab}->include($this->{$regr_dep_axis}->[$ix],$datlist);
	    } else {
		$nrej++;
	    }
	}
	$stable_rejection=($nrej==$last_nrej)?1:0;
	$last_nrej=$nrej;
	foreach my $lab (keys %labs) {
	    $rms->{$lab} = sqrt($rgressn->{$lab}->sigmasq()+pow(1e-3,2));
	    my $rgr=$rgrs->{$lab};
	    $rgr->{"theta"}=[$rgressn->{$lab}->theta()];
	}
	$iter++;
    } while (($iter<=2) || ($stable_rejection!=1));

    # regressions are stored
    
    # pass through one more time to assign a mask array (for data point rejection downstream)
#    open(GGGG,">","outliers.qdp") || die;
    my $outlier_ix_list={};
    {
	foreach my $ix (@{$ix_list}) {
	    my $lab=$this->{"label"}->[$ix];
	    $outlier_ix_list->{$lab}=[] if (!defined($outlier_ix_list->{$lab}));
	    my $rgr=$rgrs->{$lab};
	    my ($data,$model)=($this->{$rgr->{"regr_dep_axis"}}->[$ix],0);
	    foreach my $ia_ix (0..$#{$rgr->{"regr_indep_axes"}}) {
		my $ia_val=$this->{$rgr->{"regr_indep_axes"}->[$ia_ix]}->[$ix];
		my $rgr_coeff=$rgr->{"theta"}->[$ia_ix];
		$model += $ia_val*$rgr_coeff;
	    }	    
	    $outlier_ix_list->{$lab}->[$ix]=($data-$model)/$rms->{$lab};
#	    if (sqrt(pow(($data-$model)/$rms->{$lab},2)) > $thresh_rms) {
#		# this is an outlier. assign like this for random access
#		printf GGGG "%g %g %g %g\n",
#		    $this->{$rgr->{"regr_indep_axes"}->[1]}->[$ix],
#		    $this->{$rgr->{"regr_indep_axes"}->[2]}->[$ix],
#		    $outlier_ix_list->{$lab}->[$ix],
#		    $outlier_ix_list->{$lab}->[$ix]*$rms->{$lab};
#	    }
	}
    }
#    close(GGGG);
#    exit;
    
    # now since the regression is patchwork, store columns corresponding to the regression and the residuals here, and append them to $this
    {
	# these are the columns that can be appended
	my ($newcol_regmodel,$newcol_regmodelsub)=([],[]); 
	foreach my $ix (@{$ix_list}) {
	    my $lab=$this->{"label"}->[$ix];
	    my $rgr=$rgrs->{$lab};
	    my ($data,$model)=($this->{$regr_dep_axis}->[$ix],0);
	    foreach my $ia_ix (0..$#{$regr_indep_axes}) {
		my $ia_val=$this->{$regr_indep_axes->[$ia_ix]}->[$ix];
		my $rgr_coeff=$rgr->{"theta"}->[$ia_ix];
		$model += $ia_val*$rgr_coeff;
	    }
	    # ready to store
	    $newcol_regmodel->[$ix]=$model;
	    $newcol_regmodelsub->[$ix]=($data-$model);
	}
	append_column($this,$regr_dep_axis."_pwl",$newcol_regmodel);
	append_column($this,$regr_dep_axis."_pwl_rr",$newcol_regmodelsub);
    }
    return($outlier_ix_list);
}

sub regr_windowed_surface {
    my ($this,$new_rgr,$regr_indep_axes,$regr_dep_axis,$starting_ix_list,$thresh_rms)=@_;

    if (!defined($this)) {
	printf STDERR "entry $this doesn't exist.\nexiting..\n";
	exit(1);
    }

    if (!defined($this->{$regr_dep_axis})) {
	printf STDERR "dependent axis $regr_dep_axis not defined in $this.\nexiting..\n";
	exit(1);
    }
    foreach my $ia (@{$regr_indep_axes}) {
	if (!defined($this->{$ia})) {
	    printf STDERR "independent axis $ia not defined in $this.\nexiting..\n";
	    exit(1);
	}
    }

    $this->{$new_rgr}={};
    $this->{$new_rgr}->{"regr"}={};
    my $rgr=$this->{$new_rgr}->{"regr"};
    $rgr->{"regr_indep_axes"}=$regr_indep_axes;
    $rgr->{"regr_dep_axis"}=$regr_dep_axis;
    my $ix_list=[@{$starting_ix_list}];
    my $iter=0;
    my $nrej=0;
    my $last_nrej=0;
    my $rms;
    my $stable_rejection;
    do {
	my $rgressn=Statistics::Regression->new($regr_dep_axis,$regr_indep_axes);
	$nrej=0;
	foreach my $ix (@{$ix_list}) {
	    my ($data,$model)=(0,0);
	    if ($iter!=0) {
		($data,$model)=($this->{$rgr->{"regr_dep_axis"}}->[$ix],0);
		foreach my $ia_ix (0..$#{$rgr->{"regr_indep_axes"}}) {
		    my $ia_val = $this->{$rgr->{"regr_indep_axes"}->[$ia_ix]}->[$ix];
		    my $rgr_coeff=$rgr->{"theta"}->[$ia_ix];
		    $model += $ia_val*$rgr_coeff;
		}
	    }
	    if (($iter==0)||(sqrt(pow(($data-$model)/$rms,2))<$thresh_rms)) {
		my $datlist=[];
		foreach my $ia (@{$rgr->{"regr_indep_axes"}}) {
		    push(@{$datlist},$this->{$ia}->[$ix]);
		}
		$rgressn->include($this->{$regr_dep_axis}->[$ix],$datlist);
	    } else {
		$nrej++;
	    }
	}
	$stable_rejection=($nrej==$last_nrej)?1:0;
	$last_nrej=$nrej;
	$rms = sqrt($rgressn->sigmasq()+ pow(1e-3,2));
	$rgr->{"theta"}=[$rgressn->theta()];
	$iter++;
    } while (($iter<=2) || ($stable_rejection!=1));
    # regression is already stored. return control to caller.
}

sub regression_difference {
    my ($this,$new_regr,$regr_indep_axes,$regr_dep_axis,$r1,$r2)=@_;
    $this->{$new_regr}={};
    $this->{$new_regr}->{"regr"}={};
    my $rgr=$this->{$new_regr}->{"regr"};
    $rgr->{"regr_indep_axes"}=$regr_indep_axes;
    $rgr->{"regr_dep_axis"}=$regr_dep_axis;
    
    my $diff=[];
    foreach my $r_ix (0..$#{$r1}) {
	$diff->[$r_ix] = $r1->[$r_ix] - $r2->[$r_ix];
    }
    $rgr->{"theta"}=$diff;
    return($diff);
}

sub regr_sample_rgns {
    my ($thedb,$rgr,$lc,$indep_axes,$dep_axis,$samp_lc,$tol)=@_;

    if (!defined($thedb->{$lc->[0]}) || 
	!defined($thedb->{$lc->[1]}) ||
	!defined($thedb->{$dep_axis})) {
	printf STDERR "either $lc->[0], $lc->[1] or $dep_axis are not defined in $thedb.\n";
	printf STDERR "exiting..\n";
	exit(1);
    }
    foreach my $ia (@{$indep_axes}) {
	if (!defined($thedb->{$ia})) {
	    printf STDERR "$ia is not defined in $thedb.\n";
	    printf STDERR "exiting..\n";
	    exit(1);
	}
    }
    
    my $regr_indep_axes=$indep_axes;
    my $regr_dep_axis=$dep_axis;
    my $rgressn=Statistics::Regression->new($regr_dep_axis,$regr_indep_axes);
    for (my $i=0;$i<$thedb->{"n_entry"};$i++) {
	# compute distance to sampling point(s). Include if accepted.
	my $accept=0;
	foreach my $sample_coord (@{$samp_lc}) {
	    my $r2=0;
	    foreach my $coord_ix (0..$#{$lc}) {
		$r2 += pow(($thedb->{$lc->[$coord_ix]}->[$i]-
			    $sample_coord->[$coord_ix]),2);
	    }
	    if ($r2 < pow($tol,2)) {
		$accept=1;
		last;
	    }
	}
	if ($accept==1) {
	    my $dep=$thedb->{$regr_dep_axis}->[$i];
	    my %indep=();
	    for (my $ria_ix=0;$ria_ix<=$#{$regr_indep_axes};$ria_ix++) {
		$indep{$regr_indep_axes->[$ria_ix]}=
		    $thedb->{$regr_indep_axes->[$ria_ix]}->[$i];
	    }
	    $rgressn->include($dep,[@indep{@{$regr_indep_axes}}]);
      }
    }

    # package up results in $thedb->{$rgr}
    my $result_rgr = [$rgressn->theta()];
    $thedb->{$rgr}={};
    $thedb->{$rgr}->{"regr"}={};
    $thedb->{$rgr}->{"regr"}->{"regr_indep_axes"}=$regr_indep_axes;
    $thedb->{$rgr}->{"regr"}->{"regr_dep_axis"}=$regr_dep_axis;
    $thedb->{$rgr}->{"regr"}->{"theta"}=$result_rgr;

    printf STDERR "%s\n",join(' ',@{$result_rgr});
    return([$rgressn->theta()]);
}

sub append_trans_coords {
    my ($this,$new_lat_coords,$trans_spec,$lat_coords)=@_;
    my @lc = ($this->{$lat_coords->[0]},$this->{$lat_coords->[1]});
    my @nlc=([],[]);
    my $theta = $trans_spec->{"theta"};
    my ($sn,$cs)=(sin($theta),cos($theta));
    for (my $i=0;$i<$this->{"n_entry"};$i++) {
	# subtract off raft_offset prior to reversing the rotation. 
	# then apply the MCS offset.
	my $coord=[];
	foreach my $cix (0,1) {
	    $coord->[$cix] = $lc[$cix]->[$i]-$trans_spec->{"raft_offset"}->[$cix];
	}
	($nlc[0]->[$i],
	 $nlc[1]->[$i])=(($coord->[0]*$cs+$coord->[1]*$sn)
			 -$trans_spec->{"MCS_offset"}->[0],
			 (-$coord->[0]*$sn+$coord->[1]*$cs)
			 -$trans_spec->{"MCS_offset"}->[1]);
    }
    foreach my $cix (0,1) {
	append_column($this,$new_lat_coords->[$cix],$nlc[$cix]);
    }
}

sub export_file {
    my ($this,$output_filename,$exclude_list,$idx_list)=@_;

    save_regressions($this,$output_filename."_.rgrs");

    # make up list of output column names
    my $output_colnames=[];
    foreach my $colname (@{$this->{"colnames"}}) {
	my $found=0;
	foreach my $exclude (@{$exclude_list}) {
	    $found=1 if ($colname eq $exclude);		
	}
	push(@{$output_colnames},$colname) if (!$found);
    }

    printf STDERR "will export file %s containing the following column titles:\n%s\n",$output_filename,join(' ',@{$output_colnames});
    
    # proceed to output the resulting output file
    open(Q,">",$output_filename) || die "can't open output $output_filename\n";
    printf Q "rereferenced_ts5_data\n";
    printf Q "%s\n",join("\t",@{$output_colnames});
    foreach my $ix (@{$idx_list}) {
	my $output_str=[];
	foreach my $outcol (@{$output_colnames}) {
	    push(@{$output_str},sprintf("%s",$this->{$outcol}->[$ix]));
	}
	printf Q "%s\n",join(' ',@{$output_str});
    }
    close(Q);
}

sub append_diff {
    my ($this,$difflist,$diffname)=@_;
    my $diff=[];
    for (my $i=0;$i<$this->{"n_entry"};$i++) {
	$diff->[$i] = ($this->{$difflist->[0]}->[$i] - $this->{$difflist->[1]}->[$i]);
    }
    append_column($this,$diffname,$diff);
}

sub populate_ref_system {
    my ($this,$split_field_names,$ref_col_name,$sort_term)=@_;
    my ($rrf,$ms)=@{$split_field_names};
    my $verbose=0;
    my $ref_system=[];
    # generate sort_term choices
    my $reref=$this->{$rrf};
    my $reref_times=[];
#    if ($#{$reref} == -1) {
#	# if there are no rereference sets, use zeros
#	append_column($this,$ref_col_name,[(0)x$this->{"n_entry"}]);
#	return;
#    }
    foreach my $reref_ix (0..$#{$reref}) {
	push(@{$reref_times},$reref->[$reref_ix]->{"regr"}->{$sort_term});
    }
    # for each measurement ($rrf & $ms entries combined)
    for (my $ix=0;$ix<$this->{"n_entry"};$ix++) {
	my $st=$this->{$sort_term}->[$ix];
	# find the nearest neighbors in the sort_term from the rerefernce choices
	# NB - the old way we hadn't been moving aero_z value, now we are (for SELFCAL)
	# SELFCAL data sets are delimited by REREF, with aero_z changes in between.
	my @st_ix;
	my ($t0,$t1);
	my @weight;

	my $bracket_rix = bsearch_index 
	{(($st-$reref_times->[$_])*
	  ($reref_times->[$_+1]-$st)>0)?0:(($st-$reref_times->[$_+1]>0)?-1:+1)} 
	(0..$#{$reref}-1);

	if ($bracket_rix==-1) {
	    @st_ix=(sort {pow($reref_times->[$a]-$st,2) <=> pow($reref_times->[$b]-$st,2)} 
		    (0..$#{$reref}))[0,1];
	} else {
	    @st_ix=($bracket_rix,$bracket_rix+1);
	}

	# @st_ix now contains 2 indices that bracket sort term $st, *or* they are the two
	# nearest indices if the sort term is not bracketed.
	
	($t0,$t1)=($reref_times->[$st_ix[0]],$reref_times->[$st_ix[1]]);
	@weight=(($t1-$st)/($t1-$t0),($st-$t0)/($t1-$t0));

	my $evaluated_regression=[];

	foreach my $r_ix (0,1) {
	    # the regression
	    my $rgr=$reref->[$st_ix[$r_ix]]->{"regr"};
	    my $theta=$rgr->{"theta"};
	    my $regr_indep_axes=$rgr->{"regr_indep_axes"};
	    # the independent 
	    my $indep_vals=[];
	    foreach my $axis (@{$regr_indep_axes}) {
		push(@{$indep_vals},$this->{$axis}->[$ix]);
	    }
	    $evaluated_regression->[$r_ix]=0;
	    foreach my $axis_ix (0..$#{$theta}) {
		$evaluated_regression->[$r_ix] += $theta->[$axis_ix]*$indep_vals->[$axis_ix];
	    }
	    if ($verbose && ($this->{"label"}->[$ix] ne "REREF")) {
		printf STDERR ("%d: (regression evaluates to %g)\naxes: %s\ncoeffs: %s\nvals: %s\n",
			       $r_ix,
			       $evaluated_regression->[$r_ix],
			       join(' ',@{$regr_indep_axes}),
			       join(' ',@{$theta}),
			       join(' ',@{$indep_vals}));
	    }
	}
	my $interpolated_regression=0;
	foreach my $i (0,1) {
	    $interpolated_regression += $evaluated_regression->[$i]*$weight[$i];
	}
	if ($verbose && ($this->{"label"}->[$ix] ne "REREF")) {
	    printf STDERR ("rerefs nearest to sort_term %g are %g[%d]: %g ".
			   "(weight %g) and %g[%d]: %g (weight %g)\ninterpolated regression=%g\n",
			   $st,
			   $reref_times->[$st_ix[0]],
			   $st_ix[0],$evaluated_regression->[0],$weight[0],
			   $reref_times->[$st_ix[1]],
			   $st_ix[1],$evaluated_regression->[1],$weight[1],
			   $interpolated_regression);
	}
	$ref_system->[$ix]=$interpolated_regression;
    }
    append_column($this,$ref_col_name,$ref_system);
}

sub populate_reref_regressions {
    my ($this,$rrf,$regr_indep_axes,$regr_dep_axis,$sort_term)=@_;
    my $verbose=0;
    open(REG,">","reref_regressions.txt") || die;
    foreach my $reref_entry (@{$this->{$rrf}}) {
	my $st=0;
	my $n_st=0;
	my $rgressn=Statistics::Regression->new($regr_dep_axis,$regr_indep_axes);
	foreach my $ix (@{$reref_entry->{"ixs"}}) {
	    my %indep=();
	    my $dep;
	    foreach my $regr_indep (@{$regr_indep_axes}) {
		if ($verbose) {
		    printf STDERR "%s: %g ",$regr_indep,$this->{$regr_indep}->[$ix];
		}
		$indep{$regr_indep}=$this->{$regr_indep}->[$ix];
	    }
	    # and the dependent term
	    if ($verbose) {
		printf STDERR ("%s: %g sort %s: %g\n",
			       $regr_dep_axis,$this->{$regr_dep_axis}->[$ix],
			       $sort_term,$this->{$sort_term}->[$ix]);
	    }
	    
	    $st += $this->{$sort_term}->[$ix];
	    $n_st++;
	    $dep=$this->{$regr_dep_axis}->[$ix];
	    $rgressn->include($dep,[@indep{@{$regr_indep_axes}}]);
	}
# 	$rgressn->print();
	my $result_rgr=[$rgressn->theta()];

	if ($verbose) {
	    printf STDERR "theta: %s\n",join (' ',@{$result_rgr});
	    printf STDERR "ave(%s): %g\n\n",$sort_term,$st/$n_st;
	}
	
	$reref_entry->{"regr"}={};
	$reref_entry->{"regr"}->{"sort_term"}=$sort_term;
	$reref_entry->{"regr"}->{$sort_term}=$st/$n_st;
	$reref_entry->{"regr"}->{"regr_indep_axes"}=$regr_indep_axes;
	$reref_entry->{"regr"}->{"regr_dep_axis"}=$regr_dep_axis;
	$reref_entry->{"regr"}->{"theta"}=$result_rgr;

	if ($verbose) {
	    printf STDOUT "%g %s\n",$st/$n_st,join(' ',@{$result_rgr});
	}
	
	printf REG "%g %s\n",$st/$n_st,join(' ',@{$result_rgr});
    }
    close(REG);
}

sub split_selfcal_meas {
    my ($this,$split_field_names,$selfcal_label)=@_;
    # ($db->[$fn_ix],["_selfcal","_meas"],"SELFCAL","aero_z");
    my ($selfcal,$ms)=@{$split_field_names};
    if (!defined($this->{$selfcal})) {
	$this->{$selfcal}=[];
    }
    if (!defined($this->{$ms})) {
	printf STDERR "array $ms expected to be defined.\nexiting..\n";
	exit(1);
    }
    my $meas=$this->{$ms};
    my @to_remove=();
    for (my $ix=0;$ix<=$#{$meas};$ix++) {
	if ($this->{"label"}->[$meas->[$ix]] =~ /SELFCAL/) {
	    # stage to remove this $ix from array $meas..
	    push(@to_remove,$ix);
	}
    }
    foreach my $ix (reverse @to_remove) {
	push(@{$this->{$selfcal}},splice(@{$meas},$ix,1));
    }
    # now sift selfcal data sets according to label & aero_z.
    $this->{"SELFCAL"}={} if (!defined($this->{"SELFCAL"}));
    foreach my $six (@{$this->{$selfcal}}) {
	my $lab=$this->{"label"}->[$six];
	my $surface=$lab;
	$surface =~ s/SELFCAL_//;
	$this->{"SELFCAL"}->{$surface}=[] if (!defined($this->{"SELFCAL"}->{$surface}));
	push(@{$this->{"SELFCAL"}->{$surface}},$six);
    }
    my $rgressn={};
    foreach my $surface (sort keys %{$this->{"SELFCAL"}}) {
	my $ix_list=$this->{"SELFCAL"}->{$surface};
	$rgressn->{$surface}=Statistics::Regression->new("_SELFCAL_".$surface,
							  ["I","aero_y","aero_z"]);
	foreach my $ix (@{$ix_list}) {
	    my $datlist=[];
	    foreach my $ia ("I","aero_y","aero_z") {
		push(@{$datlist},$this->{$ia}->[$ix]);
	    }
	    $rgressn->{$surface}->include($this->{"key_z2"}->[$ix],$datlist);
	}
#	$rgressn->{$surface}->print();
	my $coeffs={};
	@{$coeffs}{"I","aero_y","aero_z"}=($rgressn->{$surface}->theta());
	$coeffs->{"aero_z_corr"} = $coeffs->{"aero_z"}-$coeffs->{"aero_y"}*tan(8.5*atan2(1,1)/45.0);
	
	printf STDOUT ("for surface $surface (%s):\ncoeff(I)=%g\ncoeff(aero_y)=%g\ncoeff(aero_z)=%g\n",
		       sqrt($rgressn->{$surface}->sigmasq()),
		       $coeffs->{"I"},$coeffs->{"aero_y"},$coeffs->{"aero_z"});
	printf STDOUT ("\tcorrected coeff(aero_z)=%g\n",$coeffs->{"aero_z_corr"});
	printf STDOUT ("\ttheta = %g vs. %g\n",
		       45/atan2(1,1)*acos(1/$coeffs->{"aero_z_corr"}),
		       45/atan2(1,1)*acos(1/$coeffs->{"aero_z"}));
    }
}

sub split_reref_meas {
    my ($this,$split_field_names,$reref_label)=@_;
    # generate sub-arrays containing indices
    my ($rrf,$ms)=@{$split_field_names};
    foreach my $field ($rrf,$ms) {
	if (!defined($this->{$field})) {
	    $this->{$field}=[];
	} else {
	    printf STDERR "array $field already defined in $this.\nexiting..\n";
	    exit(1);
	}
    }

    # now pass through the data space and allocate array entries as needed.
    my $is_reref=0;
    my $this_reref=-1;
    my $last_aero_z=-1;
    for (my $ix=0;$ix<$this->{"n_entry"};$ix++) {
	if ($this->{"label"}->[$ix] eq $reref_label) {
	    if ($is_reref && ($this->{"aero_z"}->[$ix] == $last_aero_z)) { # still in sequence of reref values. append to existing list
	    } else {
		# append a new reref entry to $this->{"_reref"}
		$this_reref++;
		$this->{$rrf}->[$this_reref]={};
		$this->{$rrf}->[$this_reref]->{"ixs"}=[];
	    }
	    push(@{$this->{$rrf}->[$this_reref]->{"ixs"}},$ix);
	    $last_aero_z=$this->{"aero_z"}->[$ix];
	    $is_reref=1;
	} else {
	    $is_reref=0;
	    push(@{$this->{$ms}},$ix);
	}
    }
    return;
    # now check to see what reref looks like.
    printf STDERR "number of groups: %d\n",$#{$this->{$rrf}}-$[+1;
    for (my $grp_ix=0;$grp_ix<=$#{$this->{$rrf}};$grp_ix++) {
	my $this_group=$this->{$rrf}->[$grp_ix]->{"ixs"};
	printf STDERR "\tfrom %d to %d (\#entries: %d)\n",@{$this_group}[0,$#{$this_group}],$#{$this_group}-$[+1;
    }
    printf STDERR ".. and data field is %d long.\n",$#{$this->{$ms}}-$[+1;
#    exit;
}

sub append_sum {
    my ($this,$sumlist,$sum_name)=@_;
    my $zsum=[];
    for (my $ix=0;$ix<$this->{"n_entry"};$ix++) {
	$zsum->[$ix]=0;
	foreach my $arry (@{$sumlist}) {
	    $zsum->[$ix] += $this->{$arry}->[$ix];
	}
    }
    append_column($this,$sum_name,$zsum);
}

sub append_column {
    my ($this,$col_name,$col_data)=@_;
    if (!defined($this->{$col_name})) {
	$this->{$col_name}=$col_data;
	push(@{$this->{"colnames"}},$col_name);
    } else {
	printf STDERR "column $col_name already defined in $this.\nexiting..\n";
	exit(1);
    }
}

sub detach_column {
    my ($this,$col_name)=@_;
    foreach my $cnix (0..$#{$this->{"colnames"}}) {
	next if (defined($this->{"colnames"}->[$cnix]) &&
		 ($this->{"colnames"}->[$cnix] ne $col_name));
	# this will also splice out any undefined elements in the "colnames" array
	splice(@{$this->{"colnames"}},$cnix,1);
    }
    if (defined($this->{$col_name})) {
	undef($this->{$col_name});
    } else {
	printf STDERR "column $col_name doesn't exist in $this.\nexiting..\n";
	exit(1);
    }
}

sub describe_contents {
    my ($this)=@_;
    printf STDERR ("currently have %d entries with column titles:\n%s\n",
		   $this->{"n_entry"},
		   join(' ',@{$this->{"colnames"}}));
}

sub read_scan_contents {
    my ($this,$gain)=@_;
    open(F,$this->{"filename"}) || die;
    my $strip_counter=0;
    $this->{"n_entry"}=0 if (!defined($this->{"n_entry"}));
    if (defined($gain)) {
	printf STDERR "will attempt to apply the following gain corrections:\n";
	my %gns=%{$gain->{"gain"}};
	while (my ($key,$val)= each %gns) {
	    printf STDERR "\t%s: %s\n",$key,$val;
	}
    }
    while (<F>) {
	chomp;
	if (/\#/) {
	    if (/TF/) {
		$this->{"TF"}={} if (!defined($this->{"TF"}));
		my ($key,$val)=($_ =~ /(\S+)\s*=\s*(\S+)/);
		$this->{"TF"}->{$key}=$val;
	    }
	    # nominally should expect a transform specification (TF)
	    # to contain keyword/values for X0, Y0, theta which should be traced to metro_scan.perl
	    next;
	}

	next if (/FFF/);
#	next if (/SELFCAL/); # dont include selfcal in data

	$this->{"hdr"}=$_ if ($strip_counter==0); # probably won't use it, save it for now
	if ($strip_counter==1) {
	    $this->{"colnames"}=[split('\t')];
	    foreach my $colname (@{$this->{"colnames"}}) {
		$this->{$colname} = [];
	    }
	}
	if ($strip_counter>1) { # read data content
	    my @contents = split(' ');
	    foreach my $ix (0..$#contents) {
		my $cn=$this->{"colnames"}->[$ix];
		if (defined($gain) && defined($gain->{"gain"}->{$cn})) {
		    push(@{$this->{$cn}},$contents[$ix]*$gain->{"gain"}->{$cn});
		} else {
		    push(@{$this->{$cn}},$contents[$ix]);
		}
	    }
	    $this->{"n_entry"}++;
	}
	$strip_counter++;
    }
    close(F);
}

sub stash_fits_version {
    my ($fptr,$this,$include_regions,$exclude_columns,$extension_name)=@_;
    my $status=0;
    my $tfields=0;
    my ($ttype,$tform,$tunit,$dtype)=([],[],[],[]);
    my $extname="the_data";
    my @incl_cols=();
    foreach my $col (@{$this->{"colnames"}}) {
	my $skip_col=0;
	foreach my $excl_col (@{$exclude_columns}) {
	    $skip_col=1 if ($col eq $excl_col);
	}
	next if ($skip_col);
	push(@incl_cols,$col);
	if ($col eq "label") {
	    push(@{$tform},"40A");
	    push(@{$dtype},TSTRING);
	    push(@{$tunit},"surface part label");
	} else {
	    if ($col =~ /Temp/) {
		push(@{$tunit},"Celsius");
	    } else {
		push(@{$tunit},"millimeters");
	    }
	    push(@{$tform},"1E");
	    push(@{$dtype},TDOUBLE);
	}
	my $fieldname=$col;
	$fieldname =~ tr / /_/;
	push(@{$ttype},$fieldname);
	$tfields++;
    }
    $fptr->create_tbl(BINARY_TBL,0,
		      $tfields,$ttype,$tform,$tunit,$extension_name,$status);
    printf "status=$status\n" if ($status);
    foreach my $col_ix (0..$#incl_cols) {
	my $colname=$incl_cols[$col_ix];
	if ($include_regions->{"labels"} eq "all") {
	    $fptr->write_col($dtype->[$col_ix],
			     $col_ix+1,1,1,
			     $#{$this->{$colname}}-$[+1,
			     $this->{$colname},$status);
	    printf "status=$status\n" if ($status);
	} else {
	    my $row=0;
	    for (my $i=0;$i<=$#{$this->{$colname}};$i++) {
		# check for the label field for this entry
		my $include_this=0;
		foreach my $lbl (@{$include_regions->{"labels"}}) {
		    $include_this=1 if ($lbl eq $this->{"label"}->[$i]);
		}
		next if (!$include_this);
		next if (!defined($this->{$colname}->[$i]));
		$fptr->write_col($dtype->[$col_ix],
				 $col_ix+1,$row+1,
				 1,1,[$this->{$colname}->[$i]],$status);
		printf "status=$status\n" if ($status);
		$row++;
	    }
	}
    }
}

sub stash_regressions_fits_version {
    my ($fptr,$this)=@_;
    # the part to save regressions to the "regress" extension in the fits file
    my $status=0;
    $fptr->movnam_hdu(BINARY_TBL,"REGRESSIONS",0,$status);
    my ($tfields,$ttype,$tform,$tunit,$dtype,$extionsion_name)=
	(8,["regression_name","referenced against",
	    "indep_axis_z","indep_axis_x","indep_axis_y",
	    "coeff._z0","coeff._dz_dx","coeff._dz_dy"],
	 ["40A","40A","40A","40A","40A","1E","1E","1E"],
	 ["identifier","column name","column name","column name","column name",
	  "mm","mm/mm","mm/mm"],
	 [TSTRING,TSTRING,TSTRING,
	  TSTRING,TSTRING,TDOUBLE,
	  TDOUBLE,TDOUBLE],"REGRESSIONS");
    if ($status == 301) {
	# create this new extension
	$status=0;
	$fptr->create_tbl(BINARY_TBL,0,$tfields,$ttype,$tform,$tunit,$extionsion_name,$status);
	printf "status=$status\n" if ($status);
    }
    # extension exists, carry on here.
    foreach my $key (sort keys %{$this}) {
	if ((ref $this->{$key} eq ref {}) &&
	    defined($this->{$key}->{"regr"})) {
	    my @data=($key,$this->{$key}->{"regr"}->{"regr_dep_axis"},
		      @{$this->{$key}->{"regr"}->{"regr_indep_axes"}},
		      @{$this->{$key}->{"regr"}->{"theta"}});
	    next if ($#data-$[+1 != 8);
	    # get the current number of rows.
	    my $nrows;
	    $fptr->get_num_rows($nrows,$status);
	    printf "status=$status\n" if ($status);
	    for (my $col=0;$col<$tfields;$col++) {
		$fptr->write_col($dtype->[$col],$col+1,$nrows+1,1,1,[$data[$col]],$status);
		printf "status=$status\n" if ($status);
	    }
	}
    }

    return if (!(defined($this->{"_reref"}) && (ref $this->{"_reref"} eq ref [])));
    $fptr->movnam_hdu(BINARY_TBL,"REREF_REGR",0,$status);
    ($tfields,$ttype,$tform,$tunit,$dtype,$extionsion_name)=
	(7,["timestamp",
	    "indep_axis_z","indep_axis_x","indep_axis_y",
	    "coeff._z0","coeff._dz_dx","coeff._dz_dy"],
	 ["1E","40A","40A","40A","1E","1E","1E"],
	 ["seconds","column name","column name","column name",
	  "mm","mm/mm","mm/mm"],
	 [TDOUBLE,
	  TSTRING,TSTRING,TSTRING,
	  TDOUBLE,TDOUBLE,TDOUBLE],"REREF_REGR");
    if ($status == 301) {
	# create this new extension
	$status=0;
	$fptr->create_tbl(BINARY_TBL,0,$tfields,$ttype,$tform,$tunit,$extionsion_name,$status);
	printf "status=$status\n" if ($status);
    }
    # extension exists, carry on here.
    foreach my $entry (@{$this->{"_reref"}}) {
	next if (!defined($entry->{"regr"}));
	my $st=$entry->{"regr"}->{"sort_term"};
	my @data=($entry->{"regr"}->{$st},
		  @{$entry->{"regr"}->{"regr_indep_axes"}},
		  @{$entry->{"regr"}->{"theta"}});
	# get the current number of rows.
	my $nrows;
	$fptr->get_num_rows($nrows,$status);
	printf "status=$status\n" if ($status);
	for (my $col=0;$col<$tfields;$col++) {
	    $fptr->write_col($dtype->[$col],$col+1,$nrows+1,1,1,[$data[$col]],$status);
	    printf "status=$status\n" if ($status);
	}
    }
}

sub pare_array {
    my ($ix_array,$outlier_hash,$labels,$thresh)=@_;
    my @targeted_indices=();
    foreach my $label (@{$labels}) {
	foreach my $ix (keys @{$outlier_hash->{$label}}) {
	    push(@targeted_indices,$ix) 
		if (pow($outlier_hash->{$label}->[$ix],2)>pow($thresh,2));
	}
    }
    @targeted_indices = sort {$a<=>$b} @targeted_indices;

    foreach my $ix (reverse (0..$#{$ix_array})) {
	next if ($ix_array->[$ix] != $targeted_indices[$#targeted_indices]);
	splice(@targeted_indices,$#targeted_indices,1);
	splice(@{$ix_array},$ix,1);
	last if ($#targeted_indices==-1);
    }
}
