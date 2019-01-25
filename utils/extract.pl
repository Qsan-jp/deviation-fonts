#!/usr/bin/perl
use strict;
use warnings;
use Getopt::Long;

sub parse {
    my($file) =@_;
    open my $fh, $file or die "Can't read $file\n";
    my $char;
    my $data;
    my $chardef = {};
    my $header = "";
    while(<$fh>) {
        $header .= $_ if(/^STARTFONT/ .. /^ENDPROPERTIES/);
        if(/^STARTCHAR\s+(\S+)/) {
            $char = $1;
            $data = "";
        }
        $data .= $_;
        if(/^ENDCHAR/) {
            $chardef->{$char} = $data;
        }
    }
    return $chardef, $header;
}


my($outfile, $missing, $different);
GetOptions("outbdf=s" => \$outfile, "missing" => \$missing, "different" => \$different);
my ($ref, $header) = parse(shift(@ARGV));
my ($new) = parse(shift(@ARGV));

my $outchars = "";
my $count = 0;
for my $char (sort keys %$ref) {
    if (! $new->{$char}) {
        print "Missing: $char\n";
        if ($missing) {
            $count++;
            $outchars .= $ref->{$char};
        }
    } elsif($ref->{$char} ne $new->{$char}) {
        print "Different: $char\n";
        if ($different) {
            $count++;
            $outchars .= $ref->{$char};
        }
    } else {
        print "Same: $char\n";
    }
}

if ($outfile) {
    open my $fh, ">", $outfile;
    print $fh $header;
    print $fh "CHARS $count\n";
    print $fh $outchars;
    print $fh "ENDFONT\n";
    close $fh;
}
